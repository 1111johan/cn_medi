from __future__ import annotations

import json
import urllib.request

BASE = "http://127.0.0.1:8000"

DEMO_ITEMS = [
    {
        "source_type": "case",
        "title": "门诊案例：脾虚痰瘀伴胸闷",
        "content": "患者乏力胸闷2月，舌淡胖苔白腻，脉濡涩，治以健脾化痰、活血化瘀。",
        "tags": ["门诊案例", "脾虚痰瘀", "胸闷"],
        "metadata": {"department": "中医内科"},
    },
    {
        "source_type": "paper",
        "title": "证候量化研究样例",
        "content": "通过症状聚类和舌脉特征映射构建证候预测模型，提升辅助辨证一致性。",
        "tags": ["证候", "量化", "研究"],
        "metadata": {"year": 2025},
    },
    {
        "source_type": "classic",
        "title": "《伤寒论》温胆思路摘录",
        "content": "痰热内扰可见心烦不寐，治宜和胃化痰、清胆宁心。",
        "tags": ["伤寒论", "痰热扰心", "失眠"],
        "metadata": {"book": "伤寒论"},
    },
    {
        "source_type": "guideline",
        "title": "失眠中医辨证路径（示例）",
        "content": "建议按主诉、舌脉、病程、伴随症状构建证据链，再做证候排序与治法映射。",
        "tags": ["失眠", "辨证", "证据链"],
        "metadata": {"org": "MVP示例"},
    },
]


def post_json(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        url=f"{BASE}{path}",
        method="POST",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=12) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    print("== 写入知识样例 ==")
    for item in DEMO_ITEMS:
        body = post_json("/knowledge/ingest", item)
        print(body)

    print("\n== 触发智慧问答样例 ==")
    qa_payload = {
        "question": "最近口苦心烦，晚上睡不好，舌红苔黄腻，想了解中医辨证思路",
        "mode": "mixed",
        "scenario": "临床辨证",
    }
    qa_result = post_json("/smart-qa/ask", qa_payload)
    print(
        {
            "scenario": qa_result.get("scenario"),
            "risk_level": qa_result.get("risk_level"),
            "top_syndrome": (qa_result.get("result_cards", {}).get("syndrome_candidates", [{}])[0]).get("name"),
        }
    )

    print("\n== 执行闭环任务样例 ==")
    task_payload = {
        "action": "generate_summary",
        "question": qa_payload["question"],
        "scenario": qa_result.get("scenario"),
        "extracted_fields": qa_result.get("extracted_fields", {}),
        "result_cards": qa_result.get("result_cards", {}),
        "evidences": qa_result.get("evidences", []),
    }
    task_result = post_json("/smart-qa/task-execute", task_payload)
    print({"action": task_result.get("action"), "status": task_result.get("status"), "message": task_result.get("message")})


if __name__ == "__main__":
    main()
