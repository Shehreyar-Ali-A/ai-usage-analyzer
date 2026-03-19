from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Chat normalisation
# ---------------------------------------------------------------------------

RoleType = Literal["user", "assistant"]


class ChatMessage(BaseModel):
    role: RoleType
    content: str
    timestamp: Optional[str] = None


class NormalizedChat(BaseModel):
    messages: List[ChatMessage]


# ---------------------------------------------------------------------------
# Parsed structures
# ---------------------------------------------------------------------------

class ParsedSection(BaseModel):
    title: Optional[str] = None
    paragraphs: List[str] = Field(default_factory=list)


class ParsedAssignment(BaseModel):
    sections: List[ParsedSection] = Field(default_factory=list)
    full_text: str = ""
    word_count: int = 0


class ChatTurn(BaseModel):
    turn_id: int
    user_message: str
    assistant_messages: List[str] = Field(default_factory=list)
    timestamp: Optional[str] = None


class ParsedChat(BaseModel):
    messages: List[ChatMessage] = Field(default_factory=list)
    turns: List[ChatTurn] = Field(default_factory=list)
    user_prompts: List[str] = Field(default_factory=list)
    assistant_texts: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Chunks
# ---------------------------------------------------------------------------

class AssignmentChunk(BaseModel):
    chunk_id: str
    source_type: Literal["assignment"] = "assignment"
    level: Literal["document", "section", "paragraph"]
    section_title: Optional[str] = None
    paragraph_index: int = 0
    char_start: int = 0
    char_end: int = 0
    estimated_tokens: int = 0
    text: str = ""


class ChatTurnChunk(BaseModel):
    turn_id: int
    prompt_text: str = ""
    assistant_text: str = ""
    timestamp: Optional[str] = None


class AssistantOutputChunk(BaseModel):
    chunk_id: str
    source_type: Literal["assistant"] = "assistant"
    turn_id: int
    paragraph_index: int = 0
    estimated_tokens: int = 0
    text: str = ""


# ---------------------------------------------------------------------------
# Evidence / Retrieval
# ---------------------------------------------------------------------------

class EvidencePair(BaseModel):
    assignment_chunk_id: str
    assistant_chunk_id: str
    assignment_text: str
    assistant_text: str
    semantic_score: float = 0.0
    lexical_score: float = 0.0


class CoverageMetrics(BaseModel):
    assignment_coverage_ratio: float = 0.0
    section_coverage: Dict[str, float] = Field(default_factory=dict)
    mean_best_semantic: float = 0.0
    mean_best_lexical: float = 0.0


class EvidenceSet(BaseModel):
    pairs: List[EvidencePair] = Field(default_factory=list)
    coverage: CoverageMetrics = Field(default_factory=CoverageMetrics)


# ---------------------------------------------------------------------------
# LLM Structured Output schemas
# ---------------------------------------------------------------------------

class PromptIntentCategory(BaseModel):
    count: int = 0
    confidence: float = Field(0.0, ge=0.0, le=1.0)


class NotablePromptExample(BaseModel):
    prompt_excerpt: str
    classified_intent: str


class PromptIntentResult(BaseModel):
    explanation_request: PromptIntentCategory = Field(
        default_factory=PromptIntentCategory,
    )
    brainstorming_request: PromptIntentCategory = Field(
        default_factory=PromptIntentCategory,
    )
    outline_request: PromptIntentCategory = Field(
        default_factory=PromptIntentCategory,
    )
    rewrite_request: PromptIntentCategory = Field(
        default_factory=PromptIntentCategory,
    )
    debugging_request: PromptIntentCategory = Field(
        default_factory=PromptIntentCategory,
    )
    direct_answer_request: PromptIntentCategory = Field(
        default_factory=PromptIntentCategory,
    )
    full_assignment_generation_request: PromptIntentCategory = Field(
        default_factory=PromptIntentCategory,
    )
    overall_intent_profile: Literal[
        "learning_focused", "outsourcing_focused", "mixed"
    ] = "mixed"
    notable_prompt_examples: List[NotablePromptExample] = Field(
        default_factory=list,
    )
    severity_score: float = Field(0.0, ge=0.0, le=1.0)


class TransformationPairResult(BaseModel):
    pair_index: int
    relation_type: Literal[
        "direct_copy",
        "light_paraphrase",
        "heavy_paraphrase",
        "shared_ideas_only",
        "weak_match",
    ]
    transformation_degree: float = Field(0.0, ge=0.0, le=1.0)
    reasoning: str = ""


class TransformationAnalysisResult(BaseModel):
    pair_results: List[TransformationPairResult] = Field(default_factory=list)


class RelianceJudgment(BaseModel):
    reliance_band: Literal["low", "moderate", "high"] = "moderate"
    reliance_score_recommendation: int = Field(50, ge=0, le=100)
    primary_reasons: List[str] = Field(default_factory=list)
    counter_indicators: List[str] = Field(default_factory=list)
    confidence: float = Field(0.5, ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

class ScoringFactor(BaseModel):
    name: str
    weight: float
    raw_score: float = Field(0.0, ge=0.0, le=1.0)
    weighted_score: float = 0.0
    explanation: str = ""


class ScoringResult(BaseModel):
    final_score: int = Field(0, ge=0, le=100)
    label: Literal["Low", "Moderate", "High"] = "Moderate"
    factors: List[ScoringFactor] = Field(default_factory=list)
    confidence: Literal["Low", "Medium", "High"] = "Medium"


# ---------------------------------------------------------------------------
# Report (enriched)
# ---------------------------------------------------------------------------

class EvidenceItem(BaseModel):
    ai_excerpt: str
    assignment_excerpt: str
    similarity: float = Field(ge=0.0, le=1.0)
    semantic_score: float = Field(0.0, ge=0.0, le=1.0)
    lexical_score: float = Field(0.0, ge=0.0, le=1.0)
    relation_type: Optional[str] = None


class FactorBreakdown(BaseModel):
    name: str
    weight: float
    score: float
    explanation: str


class Report(BaseModel):
    summary: str
    reliance_score: int = Field(ge=0, le=100)
    reliance_label: Literal["Low", "Moderate", "High"]
    usage_type: List[str] = Field(default_factory=list)
    evidence: List[EvidenceItem] = Field(default_factory=list)
    observations: List[str] = Field(default_factory=list)
    confidence: Literal["Low", "Medium", "High"]

    prompt_intent_summary: Optional[str] = None
    transformation_findings: List[str] = Field(default_factory=list)
    factor_breakdown: List[FactorBreakdown] = Field(default_factory=list)
    increasing_factors: List[str] = Field(default_factory=list)
    decreasing_factors: List[str] = Field(default_factory=list)
    caveats: List[str] = Field(default_factory=list)


class AnalyzeResponse(BaseModel):
    report: Report
    markdown_report: str
    pdf_base64: Optional[str] = None
