from __future__ import annotations

from datetime import datetime
from typing import Any, Dict


class DocumentService:
    def draft(
        self,
        template_type: str,
        patient_info: Dict[str, Any],
        visit_data: Dict[str, Any],
        reasoning_result: Dict[str, Any],
    ) -> str:
        if template_type == "research_summary":
            return self._research_summary(visit_data, reasoning_result)
        return self._clinical_note(patient_info, visit_data, reasoning_result)

    def _clinical_note(self, patient_info: Dict[str, Any], visit_data: Dict[str, Any], reasoning: Dict[str, Any]) -> str:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines = [
            f"【门诊病历草稿】{now}",
            f"患者：{patient_info.get('name', '未填写')}  性别：{patient_info.get('gender', '未填写')}  年龄：{patient_info.get('age', '未填写')}",
            f"主诉：{visit_data.get('chief_complaint', '未填写')}",
            f"现病史：{visit_data.get('history', '未填写')}",
            f"舌象：{visit_data.get('tongue', '未填写')}  脉象：{visit_data.get('pulse', '未填写')}",
            f"辨证：{reasoning.get('syndrome', '待确认')}",
            f"病机解释：{reasoning.get('explanation', '待补充')}",
            f"治法：{reasoning.get('therapy', '待确认')}",
            f"方药草案：{reasoning.get('formula', '待确认')}",
            "医嘱：建议结合复诊与化验指标动态调整，最终处方以临床医师确认为准。",
        ]
        return "\n".join(lines)

    def _research_summary(self, visit_data: Dict[str, Any], reasoning: Dict[str, Any]) -> str:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines = [
            f"【研究摘要草稿】{now}",
            f"研究问题：{visit_data.get('question', '未填写')}",
            f"关键证候：{reasoning.get('syndrome', '未给出')}",
            f"主要证据：{reasoning.get('evidence', '待补充')}",
            f"假设结论：{reasoning.get('hypothesis', '待补充')}",
            "后续建议：补充病例分层、扩大文献样本，并进行规则一致性校验。",
        ]
        return "\n".join(lines)


document_service = DocumentService()
