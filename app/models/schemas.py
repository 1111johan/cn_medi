from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class KnowledgeIngestRequest(BaseModel):
    source_type: str = Field(..., description="classic | guideline | case | formula | herb | paper")
    title: str
    content: str
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class KnowledgeObject(BaseModel):
    object_id: str
    source_type: str
    title: str
    content: str
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class KnowledgeSearchItem(KnowledgeObject):
    snippet: str
    score: float


class KnowledgeIngestResponse(BaseModel):
    object_id: str
    index_status: str


class IntakeParseRequest(BaseModel):
    raw_text: str
    form_data: Dict[str, Any] = Field(default_factory=dict)
    transcript: Optional[str] = None


class IntakeParseResponse(BaseModel):
    standardized_fields: Dict[str, Any]
    missing_fields: List[str]
    red_flags: List[str]


class PerceptionAnalyzeRequest(BaseModel):
    image_type: str = Field(..., description="tongue | face | herb")
    observations: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class PerceptionAnalyzeResponse(BaseModel):
    labels: List[str]
    confidence: float
    alerts: List[str]


class SyndromeReasonRequest(BaseModel):
    symptoms: List[str]
    tongue_tags: List[str] = Field(default_factory=list)
    pulse_tags: List[str] = Field(default_factory=list)
    constraints: Dict[str, Any] = Field(default_factory=dict)


class SyndromeCandidate(BaseModel):
    syndrome: str
    score: float
    support_evidence: List[str]
    counter_evidence: List[str]
    explanation: str


class SyndromeReasonResponse(BaseModel):
    candidates: List[SyndromeCandidate]


class FormulaReasonRequest(BaseModel):
    syndrome: str
    contraindications: List[str] = Field(default_factory=list)
    patient_profile: Dict[str, Any] = Field(default_factory=dict)


class FormulaReasonResponse(BaseModel):
    therapy_principle: str
    base_formula: str
    modifications: List[str]
    cautions: List[str]


class ResearchQARequest(BaseModel):
    question: str
    scope: Optional[str] = None
    source_types: List[str] = Field(default_factory=list)


class EvidenceItem(BaseModel):
    object_id: str
    title: str
    source_type: str
    snippet: str
    score: float


class ResearchQAResponse(BaseModel):
    answer: str
    evidences: List[EvidenceItem]


class SmartQAAttachment(BaseModel):
    name: str
    file_type: str = Field(default="other", description="image | document | audio | other")
    text_hint: Optional[str] = None


class SmartQARequest(BaseModel):
    question: str = ""
    query: Optional[str] = None
    mode: str = Field(default="text", description="text | voice | image | document | mixed")
    scenario: Optional[str] = None
    attachments: List[SmartQAAttachment] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def normalize_question_input(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        question = str(data.get("question", "") or "").strip()
        query = str(data.get("query", "") or "").strip()
        if not question and query:
            data["question"] = query
        return data

    @model_validator(mode="after")
    def validate_question(self) -> "SmartQARequest":
        self.question = self.question.strip()
        if not self.question:
            raise ValueError("question is required")
        return self


class SmartQAResponse(BaseModel):
    answer: str
    model_name: str = ""
    speech_text: str
    risk_level: str
    boundary_notice: str
    scenario: str
    steps: List[str] = Field(default_factory=list)
    recommended_route: List[str] = Field(default_factory=list)
    evidences: List[EvidenceItem] = Field(default_factory=list)
    digital_human: Dict[str, Any] = Field(default_factory=dict)
    conversation_title: str = ""
    session_tags: List[str] = Field(default_factory=list)
    suggested_questions: List[str] = Field(default_factory=list)
    process_cards: List[Dict[str, Any]] = Field(default_factory=list)
    extracted_fields: Dict[str, Any] = Field(default_factory=dict)
    result_cards: Dict[str, Any] = Field(default_factory=dict)
    graph_links: List[Dict[str, Any]] = Field(default_factory=list)
    workflow_tasks: List[Dict[str, Any]] = Field(default_factory=list)
    missing_items: List[str] = Field(default_factory=list)


class SmartQATaskExecuteRequest(BaseModel):
    action: str
    question: str = ""
    scenario: Optional[str] = None
    case_id: Optional[str] = None
    comment: Optional[str] = None
    extracted_fields: Dict[str, Any] = Field(default_factory=dict)
    result_cards: Dict[str, Any] = Field(default_factory=dict)
    evidences: List[Dict[str, Any]] = Field(default_factory=list)


class SmartQATaskExecuteResponse(BaseModel):
    status: str
    action: str
    message: str
    task_status: str = "done"
    draft: Optional[str] = None
    review_task: Dict[str, Any] = Field(default_factory=dict)
    payload: Dict[str, Any] = Field(default_factory=dict)


class DocumentDraftRequest(BaseModel):
    template_type: str = Field(default="clinical_note", description="clinical_note | research_summary")
    patient_info: Dict[str, Any] = Field(default_factory=dict)
    visit_data: Dict[str, Any] = Field(default_factory=dict)
    reasoning_result: Dict[str, Any] = Field(default_factory=dict)


class DocumentDraftResponse(BaseModel):
    draft: str


class FeedbackSubmitRequest(BaseModel):
    case_id: str
    actor: str = "doctor"
    action: str = Field(..., description="accept | modify | reject")
    comments: Optional[str] = None
    effectiveness: Optional[str] = None
    patched_formula: Optional[str] = None

    @field_validator("action")
    @classmethod
    def normalize_action(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in {"accept", "modify", "reject"}:
            raise ValueError("action must be accept | modify | reject")
        return normalized


class FeedbackSubmitResponse(BaseModel):
    feedback_id: str
    status: str


class LoopActionRequest(BaseModel):
    case_id: str
    action: str = Field(..., description="consult | add_teaching_case | add_rule | add_retrain_sample")
    comment: Optional[str] = None


class AuditRecord(BaseModel):
    event_id: str
    timestamp: datetime
    actor: str
    event_type: str
    details: Dict[str, Any]


class PlatformOverview(BaseModel):
    knowledge_count: int
    feedback_count: int
    audit_count: int
    last_update: Optional[datetime]
