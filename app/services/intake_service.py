from __future__ import annotations

import re
from typing import Any, Dict, List

SYMPTOM_KEYWORDS = [
    "乏力",
    "胸闷",
    "心悸",
    "失眠",
    "纳差",
    "食少",
    "腹胀",
    "便溏",
    "咳嗽",
    "痰多",
    "头晕",
    "肢体困重",
]

RED_FLAG_KEYWORDS = ["胸痛", "呼吸困难", "咯血", "高热", "意识模糊", "黑便", "便血"]


class IntakeService:
    def parse(self, raw_text: str, form_data: Dict[str, Any]) -> Dict[str, Any]:
        fields: Dict[str, Any] = {}

        age_match = re.search(r"(\d{1,3})岁", raw_text)
        if age_match:
            fields["age"] = int(age_match.group(1))

        if "男" in raw_text:
            fields["gender"] = "男"
        elif "女" in raw_text:
            fields["gender"] = "女"

        duration_match = re.search(r"(\d+\s*(天|周|月|年))", raw_text)
        if duration_match:
            fields["duration"] = duration_match.group(1).replace(" ", "")

        detected_symptoms: List[str] = []
        for keyword in SYMPTOM_KEYWORDS:
            if keyword in raw_text:
                detected_symptoms.append(keyword)
        if detected_symptoms:
            fields["symptoms"] = detected_symptoms
            fields["chief_complaint"] = "、".join(detected_symptoms[:3])

        fields.update({k: v for k, v in form_data.items() if v is not None and v != ""})

        required_fields = ["chief_complaint", "duration", "tongue", "pulse", "sleep", "stool_urine"]
        missing = [f for f in required_fields if f not in fields]

        red_flags = [k for k in RED_FLAG_KEYWORDS if k in raw_text]

        return {
            "standardized_fields": fields,
            "missing_fields": missing,
            "red_flags": red_flags,
        }


intake_service = IntakeService()
