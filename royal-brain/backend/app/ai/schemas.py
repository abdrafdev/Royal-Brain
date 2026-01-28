from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.succession.schemas import SuccessionEvaluationResult

CitationCategory = Literal["applied_rule", "uncertainty", "source_conflict", "other"]


class ExplanationCitation(BaseModel):
    category: CitationCategory
    description: str


class SourceReference(BaseModel):
    id: int
    source_type: str
    citation: str
    url: str | None = None
    issued_date: str | None = None


class SuccessionExplanation(BaseModel):
    """AI explainability output.

    Always includes:
    - confidence: a deterministic numeric score (0..1)
    - sources: sources referenced/available for this explanation
    - rules_applied: machine-readable rule context used to generate the explanation
    """

    summary: str
    detailed_reasoning: str
    citations: list[ExplanationCitation]

    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    sources: list[SourceReference] = Field(default_factory=list)
    rules_applied: dict[str, Any] = Field(default_factory=dict)


class ExplainSuccessionRequest(BaseModel):
    result: SuccessionEvaluationResult


class ExplainSuccessionResponse(BaseModel):
    explanation: SuccessionExplanation
    raw_result: SuccessionEvaluationResult
