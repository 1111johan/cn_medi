from __future__ import annotations

from typing import List

TAG_MAP = {
    "tongue": {
        "淡": "舌淡",
        "红": "舌红",
        "暗": "舌暗",
        "胖": "舌胖",
        "齿痕": "齿痕舌",
        "白腻": "苔白腻",
        "黄腻": "苔黄腻",
        "薄": "苔薄",
    },
    "face": {
        "萎黄": "面色萎黄",
        "晦暗": "面色晦暗",
        "潮红": "面色潮红",
        "无华": "气色少华",
    },
    "herb": {
        "霉": "疑似霉变",
        "虫蛀": "疑似虫蛀",
        "颜色异常": "色泽异常",
    },
}

ALERT_KEYWORDS = ["紫暗", "裂纹", "厚腻", "疑似霉变", "虫蛀"]


class PerceptionService:
    def analyze(self, image_type: str, observations: List[str], notes: str | None = None) -> dict:
        mapper = TAG_MAP.get(image_type, {})
        labels: List[str] = []

        joined = " ".join(observations + ([notes] if notes else []))
        for keyword, label in mapper.items():
            if keyword in joined:
                labels.append(label)

        if not labels and observations:
            labels = observations[:3]

        confidence = 0.55 + min(0.4, 0.08 * len(labels))
        alerts = [k for k in ALERT_KEYWORDS if k in joined]

        return {
            "labels": labels,
            "confidence": round(min(confidence, 0.95), 3),
            "alerts": alerts,
        }


perception_service = PerceptionService()
