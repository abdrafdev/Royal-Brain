from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.ai.schemas import SuccessionExplanation
from app.genealogy.schemas import GenealogyCheckResponse
from app.succession.schemas import SuccessionEvaluationResult


TimeValidityStatus = Literal[
    "active",
    "historic_recognition_only",
    "invalid",
    "uncertain",
]


class TimeValidityResult(BaseModel):
    valid: bool
    status: TimeValidityStatus
    reason: str


class JurisdictionRuleCheck(BaseModel):
    allowed: bool
    conditions: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)


class JurisdictionContext(BaseModel):
    id: int
    name: str
    code: str | None
    legal_system: str | None
    nobility_abolished_date: date | None
    legal_references: list[str] | None


class JurisdictionTitleValidationRequest(BaseModel):
    person_id: int
    title_id: int
    as_of: date | None = None


class JurisdictionTitleValidationResult(BaseModel):
    person_id: int
    title_id: int
    jurisdiction: JurisdictionContext | None

    time_validity: TimeValidityResult
    jurisdiction_rules: JurisdictionRuleCheck

    genealogy: GenealogyCheckResponse
    succession: SuccessionEvaluationResult | None

    valid: bool
    confidence: float

    sources: list[int] = Field(default_factory=list)


class JurisdictionTitleValidationResponse(BaseModel):
    result: JurisdictionTitleValidationResult
    explanation: SuccessionExplanation
    audit_id: int


# Day 7 Order Validation Types
class OrderValidationRequest(BaseModel):
    order_id: int
    claimant_person_id: int
    as_of: date | None = None


class OrderValidationFactors(BaseModel):
    fons_honorum_valid: bool
    fons_honorum_detail: str
    succession_valid: bool | None  # None if not evaluated
    succession_detail: str
    jurisdiction_recognition: dict[str, list[str]]  # {recognized, not_recognized, partial}
    documentation_score: int  # 0-100
    documentation_detail: str
    timeline_issues_count: int
    timeline_detail: str


class OrderValidationResult(BaseModel):
    order_id: int
    order_name: str
    claimant_person_id: int
    classification: str  # LEGITIMATE/SELF_STYLED/DISPUTED/FRAUDULENT
    legitimacy_score: int  # 0-100
    fraud_flags: list[str]
    factors: OrderValidationFactors
    sources: list[int]


class OrderValidationResponse(BaseModel):
    result: OrderValidationResult
    explanation: SuccessionExplanation
    audit_id: int
    

class BatchOrderValidationRequest(BaseModel):
    order_ids: list[int] = Field(min_length=1)
    claimant_person_id: int


class BatchOrderValidationResponse(BaseModel):
    results: list[OrderValidationResult]
    audit_ids: list[int]


class FraudReportResponse(BaseModel):
    min_score: int
    max_score: int
    total_orders: int
    by_classification: dict[str, int]
    by_flag: dict[str, int]
    orders: list[dict[str, Any]]
