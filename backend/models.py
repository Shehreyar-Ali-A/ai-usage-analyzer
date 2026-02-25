from typing import List, Literal, Optional

from pydantic import BaseModel, Field


RoleType = Literal["user", "assistant"]


class ChatMessage(BaseModel):
    role: RoleType
    content: str
    timestamp: Optional[str] = None


class NormalizedChat(BaseModel):
    messages: List[ChatMessage]


class EvidenceItem(BaseModel):
    ai_excerpt: str
    assignment_excerpt: str
    similarity: float = Field(ge=0.0, le=1.0)


class Report(BaseModel):
    summary: str
    reliance_score: int = Field(ge=0, le=100)
    reliance_label: Literal["Low", "Moderate", "High"]
    usage_type: List[str]
    evidence: List[EvidenceItem]
    observations: List[str]
    confidence: Literal["Low", "Medium", "High"]


class AnalyzeResponse(BaseModel):
    report: Report
    markdown_report: str
    pdf_base64: Optional[str] = None

