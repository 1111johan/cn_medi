from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any, Dict, List

from app.core.audit import query_events
from app.services.feedback_service import feedback_service
from app.services.knowledge_service import knowledge_service
from app.services.professional_knowledge_service import professional_knowledge_service


class OverviewService:
    def metrics(self) -> Dict[str, Any]:
        audits = query_events(limit=10000)
        last_update = audits[0]["timestamp"] if audits else None
        parsed_last = datetime.fromisoformat(last_update) if last_update else None

        return {
            "knowledge_count": knowledge_service.count(),
            "feedback_count": feedback_service.count(),
            "audit_count": len(audits),
            "last_update": parsed_last,
        }

    def dashboard(self) -> Dict[str, Any]:
        knowledge_list = knowledge_service.all()
        feedback_list = feedback_service.all()
        audits = query_events(limit=20000)

        knowledge_count = len(knowledge_list)
        feedback_count = len(feedback_list)
        audit_count = len(audits)

        source_counter = Counter(item.get("source_type", "unknown") for item in knowledge_list)
        event_counter = Counter(item.get("event_type", "") for item in audits)

        professional_stats = professional_knowledge_service.stats()
        professional_count = int(professional_stats.get("record_count", 0))

        clinical_events = (
            event_counter.get("intake.parse", 0)
            + event_counter.get("reason.syndrome", 0)
            + event_counter.get("reason.formula", 0)
            + event_counter.get("document.draft", 0)
            + event_counter.get("feedback.submit", 0)
        )
        research_events = event_counter.get("research.qa", 0)
        rnd_events = event_counter.get("perception.analyze", 0)
        smart_qa_events = event_counter.get("smart_qa.ask", 0)

        clinical_closed_loops = min(
            event_counter.get("reason.syndrome", 0),
            event_counter.get("reason.formula", 0),
            event_counter.get("document.draft", 0),
            event_counter.get("feedback.submit", 0),
        )

        evidence_trace_ratio = 100 if research_events == 0 else min(100, 70 + research_events)
        adoption_ratio = self._estimate_adoption_ratio(feedback_list)

        loops = {
            "knowledge": self._loop_item("知识闭环", min(100, int(knowledge_count / 12 * 100)), "古籍-医案-文献-方剂统一入库"),
            "reasoning": self._loop_item("推理闭环", min(100, int(clinical_closed_loops / 10 * 100)), "检索-规则-模型-解释-人工确认"),
            "feedback": self._loop_item("反馈闭环", min(100, int(feedback_count / 15 * 100)), "采纳/修改/拒绝与疗效回流"),
            "governance": self._loop_item("治理闭环", min(100, int(audit_count / 80 * 100)), "日志、版本、权限、审计留痕"),
        }

        roadmap = [
            {
                "phase": "阶段一（0-30天）",
                "goal": "统一产品框架、知识 schema、模型网关",
                "status": "completed" if knowledge_count >= 5 else "in_progress",
                "deliverables": "平台原型、知识对象定义、接口草案",
            },
            {
                "phase": "阶段二（31-60天）",
                "goal": "打通知识中台与推理中台，形成三场景演示闭环",
                "status": "completed" if clinical_events + research_events + rnd_events + smart_qa_events >= 12 else "in_progress",
                "deliverables": "可运行 Demo、证据回链、规则推理",
            },
            {
                "phase": "阶段三（61-90天）",
                "goal": "补齐反馈、审计、指标看板，形成平台版 MVP",
                "status": "completed" if feedback_count >= 3 and audit_count >= 25 else "pending",
                "deliverables": "反馈闭环、治理看板、试点方案",
            },
            {
                "phase": "阶段四（91-180天）",
                "goal": "机构试点、文书模板打磨、稳定性提升",
                "status": "pending",
                "deliverables": "机构试点版、质量报告、案例库",
            },
        ]

        task_queue = self._build_task_queue(
            knowledge_count=knowledge_count,
            feedback_count=feedback_count,
            research_events=research_events,
            rnd_events=rnd_events,
            smart_qa_events=smart_qa_events,
            professional_count=professional_count,
            audit_count=audit_count,
        )

        recent_audits = audits[:12]

        return {
            "generated_at": datetime.utcnow().isoformat(),
            "core_metrics": {
                "knowledge_count": knowledge_count,
                "feedback_count": feedback_count,
                "audit_count": audit_count,
                "professional_record_count": professional_count,
                "clinical_closed_loops": clinical_closed_loops,
                "evidence_trace_ratio": evidence_trace_ratio,
                "adoption_ratio": adoption_ratio,
            },
            "architecture": [
                {"name": "一底座", "desc": "国产化模型与服务网关", "status": "running"},
                {"name": "知识中台", "desc": "古籍/指南/医案/方剂/药材统一 schema", "status": "running"},
                {"name": "推理中台", "desc": "规则+检索+解释+风险校验", "status": "running"},
                {"name": "临床场景", "desc": "四诊-辨证-草案-文书-反馈", "status": "running"},
                {"name": "科研场景", "desc": "问答-证据回链-案例沉淀", "status": "running"},
                {"name": "研发场景", "desc": "感知分析-关系检索-研发记录", "status": "running"},
                {"name": "智慧问答", "desc": "数字人咨询 + 多模态输入 + 边界控制", "status": "running"},
                {"name": "治理闭环", "desc": "审计日志、权限、质量评估", "status": "running"},
            ],
            "scenario_metrics": {
                "clinical_events": clinical_events,
                "research_events": research_events,
                "rnd_events": rnd_events,
                "smart_qa_events": smart_qa_events,
            },
            "loops": loops,
            "source_breakdown": dict(source_counter),
            "roadmap": roadmap,
            "task_queue": task_queue,
            "recent_audits": recent_audits,
        }

    def _loop_item(self, name: str, progress: int, desc: str) -> Dict[str, Any]:
        if progress >= 80:
            status = "healthy"
        elif progress >= 50:
            status = "watch"
        else:
            status = "risk"
        return {
            "name": name,
            "progress": progress,
            "status": status,
            "desc": desc,
        }

    def _estimate_adoption_ratio(self, feedback_list: List[Dict[str, Any]]) -> int:
        if not feedback_list:
            return 0
        accepted = sum(1 for item in feedback_list if item.get("action") in {"accept", "modify"})
        return int(accepted / len(feedback_list) * 100)

    def _build_task_queue(
        self,
        knowledge_count: int,
        feedback_count: int,
        research_events: int,
        rnd_events: int,
        smart_qa_events: int,
        professional_count: int,
        audit_count: int,
    ) -> List[Dict[str, str]]:
        tasks: List[Dict[str, str]] = []

        if knowledge_count < 20:
            tasks.append({
                "owner": "知识中台",
                "title": "补充核心对象与标签映射",
                "priority": "P0",
                "detail": "建议优先补齐证候、治法、方剂、药材、医案五类对象。",
            })

        if feedback_count < 5:
            tasks.append({
                "owner": "临床工作台",
                "title": "提升医生反馈回流量",
                "priority": "P0",
                "detail": "保证采纳/修改/拒绝动作均有样本，形成可训练闭环。",
            })

        if research_events < 8:
            tasks.append({
                "owner": "科研传承",
                "title": "构建教学案例沉淀库",
                "priority": "P1",
                "detail": "将高质量问答结果结构化回写知识中台。",
            })

        if rnd_events < 6:
            tasks.append({
                "owner": "中药研发",
                "title": "补齐方剂-药材-症状关系链",
                "priority": "P1",
                "detail": "形成可用于项目论证的关系检索样例。",
            })

        if smart_qa_events < 10:
            tasks.append({
                "owner": "智慧问答",
                "title": "提升数字人咨询覆盖",
                "priority": "P1",
                "detail": "完善临床辨证、体质调理、慢病调护三类场景问答与边界提示。",
            })

        if professional_count < 300:
            tasks.append({
                "owner": "数据工程",
                "title": "扩展专业数据库索引范围",
                "priority": "P1",
                "detail": "优先纳入结构化医案与关键古籍文本。",
            })

        if audit_count < 30:
            tasks.append({
                "owner": "治理后台",
                "title": "补齐审计覆盖率",
                "priority": "P0",
                "detail": "确保关键推理、导出、反馈、知识变更全部留痕。",
            })

        if not tasks:
            tasks.append({
                "owner": "平台运营",
                "title": "进入机构试点准备",
                "priority": "P0",
                "detail": "当前关键指标已达标，建议推进试点评估。",
            })

        return tasks[:6]


overview_service = OverviewService()
