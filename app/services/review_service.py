from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.core.config import REVIEW_TASK_FILE
from app.core.storage import JsonListStore


DEFAULT_TASKS = [
    {
        "task_type": "knowledge",
        "priority": "high",
        "status": "pending",
        "title": "证候规则冲突：痰湿瘀阻 vs 脾虚痰瘀",
        "summary": "同一组症状在两条规则上评分接近，需专家判定主证与次证边界。",
        "ai_prejudge": "建议主证：痰湿瘀阻（置信 0.63）",
        "evidence_refs": ["rule://痰湿瘀阻", "rule://脾虚痰瘀", "case://demo-2026-0419-A"],
    },
    {
        "task_type": "case",
        "priority": "medium",
        "status": "pending",
        "title": "争议案例：方药草案被医生驳回",
        "summary": "系统推荐二陈汤合血府逐瘀汤，医生改为温胆汤加减，需原因归档。",
        "ai_prejudge": "可能与患者体质偏虚及睡眠问题相关。",
        "evidence_refs": ["case://clinical-queue-002", "feedback://modify-20260419-02"],
    },
    {
        "task_type": "risk",
        "priority": "high",
        "status": "pending",
        "title": "高风险输出复核：孕期活血建议",
        "summary": "推理结果包含活血化瘀方向，触发孕期禁忌告警，需二次审查。",
        "ai_prejudge": "建议降级为人工确认，不允许自动草案直接输出。",
        "evidence_refs": ["audit://reason.formula", "policy://pregnancy-risk"],
    },
]


class ReviewService:
    def __init__(self) -> None:
        self.store = JsonListStore(REVIEW_TASK_FILE)
        self.ensure_seed_data()

    def ensure_seed_data(self) -> None:
        items = self.store.read()
        if items:
            return

        now = datetime.utcnow().isoformat()
        seeded = []
        for task in DEFAULT_TASKS:
            seeded.append(
                {
                    "task_id": str(uuid4()),
                    "created_at": now,
                    "updated_at": now,
                    "decision": None,
                    "decision_comment": None,
                    "reviewer": None,
                    **task,
                }
            )
        self.store.write(seeded)

    def list_tasks(
        self,
        status: Optional[str] = None,
        task_type: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        tasks = self.store.read()
        if status:
            tasks = [x for x in tasks if x.get("status") == status]
        if task_type:
            tasks = [x for x in tasks if x.get("task_type") == task_type]
        if priority:
            tasks = [x for x in tasks if x.get("priority") == priority]

        tasks.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return tasks[:limit]

    def create_task(
        self,
        task_type: str,
        title: str,
        summary: str,
        priority: str = "medium",
        ai_prejudge: str = "",
        evidence_refs: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        now = datetime.utcnow().isoformat()
        task = {
            "task_id": str(uuid4()),
            "task_type": task_type,
            "priority": priority,
            "status": "pending",
            "title": title,
            "summary": summary,
            "ai_prejudge": ai_prejudge,
            "evidence_refs": evidence_refs or [],
            "created_at": now,
            "updated_at": now,
            "decision": None,
            "decision_comment": None,
            "reviewer": None,
        }

        tasks = self.store.read()
        tasks.append(task)
        self.store.write(tasks)
        return task

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        for task in self.store.read():
            if task.get("task_id") == task_id:
                return task
        return None

    def decide(
        self,
        task_id: str,
        action: str,
        reviewer: str,
        comment: Optional[str] = None,
    ) -> Dict[str, Any]:
        tasks = self.store.read()
        now = datetime.utcnow().isoformat()

        updated = None
        for idx, task in enumerate(tasks):
            if task.get("task_id") != task_id:
                continue

            next_status = {
                "approve": "approved",
                "reject": "rejected",
                "modify": "modified",
                "escalate": "escalated",
            }.get(action, "pending")

            task["status"] = next_status
            task["decision"] = action
            task["decision_comment"] = comment
            task["reviewer"] = reviewer
            task["updated_at"] = now
            tasks[idx] = task
            updated = task
            break

        if updated is None:
            raise ValueError("task_not_found")

        self.store.write(tasks)
        return updated

    def stats(self) -> Dict[str, Any]:
        tasks = self.store.read()
        total = len(tasks)
        pending = len([x for x in tasks if x.get("status") == "pending"])
        escalated = len([x for x in tasks if x.get("status") == "escalated"])
        approved = len([x for x in tasks if x.get("status") == "approved"])
        rejected = len([x for x in tasks if x.get("status") == "rejected"])

        return {
            "total": total,
            "pending": pending,
            "escalated": escalated,
            "approved": approved,
            "rejected": rejected,
        }


review_service = ReviewService()
