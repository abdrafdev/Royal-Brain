from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

SuccessionStatus = Literal["VALID", "INVALID", "UNCERTAIN"]
SuccessionRuleType = Literal["agnatic", "cognatic", "salic", "semi_salic", "custom"]
Severity = Literal["info", "warning", "error"]


class CustomRule(BaseModel):
    allow_female_inheritance: bool = False
    allow_female_transmission: bool = True
    allow_adoption: bool = False
    max_depth: int | None = Field(default=12, ge=1, le=50)


class SuccessionEvaluationRequest(BaseModel):
    root_person_id: int
    candidate_person_id: int
    rule_type: SuccessionRuleType
    as_of: date | None = None
    custom_rule: CustomRule | None = None


class SuccessionReason(BaseModel):
    severity: Severity
    code: str
    message: str
    person_id: int | None = None
    relationship_id: int | None = None


class SuccessionEvaluationResult(BaseModel):
    root_person_id: int
    candidate_person_id: int
    rule_type: SuccessionRuleType
    status: SuccessionStatus
    as_of: date | None

    path_person_ids: list[int] | None = None
    relationship_ids: list[int] | None = None

    checked_paths: int
    reasons: list[SuccessionReason]

    applied_rule: CustomRule
