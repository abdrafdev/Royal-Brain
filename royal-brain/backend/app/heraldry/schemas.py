"""Heraldry schemas — Pydantic models for Day 8 API."""
from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field

from app.ai.schemas import SourceReference


class HeraldryParseRequest(BaseModel):
    """Request to parse a blazon."""
    blazon: str = Field(min_length=1, max_length=2000)


class HeraldryValidateRequest(BaseModel):
    """Request to validate heraldry."""
    blazon: str = Field(min_length=1, max_length=2000)
    jurisdiction_id: int | None = None
    claimant_person_id: int | None = None
    as_of: date | None = None
    strict_mode: bool = True


class HeraldryFullValidationRequest(BaseModel):
    """Request for full heraldic validation with all engines."""
    blazon: str = Field(min_length=1, max_length=2000)
    jurisdiction_id: int
    claimant_person_id: int | None = None
    as_of: date | None = None
    strict_mode: bool = True
    generate_svg: bool = True


class ParsedBlazonResponse(BaseModel):
    """Response with parsed blazon structure."""
    field_tincture: str
    field_tincture_type: str
    charges: list[dict]
    ordinaries: list[dict]
    partitions: list[dict]
    valid: bool
    errors: list[str]
    raw_blazon: str


class RuleViolationResponse(BaseModel):
    """Response for a heraldic rule violation."""
    rule_name: str
    severity: str
    message: str
    element: str | None = None


class ValidationResultResponse(BaseModel):
    """Response with heraldic validation results."""
    valid: bool
    violations: list[RuleViolationResponse]
    warnings: list[RuleViolationResponse]
    pass_rules: list[str]


class JurisdictionComplianceResponse(BaseModel):
    """Response with jurisdiction compliance."""
    compliant: bool
    jurisdiction_code: str
    jurisdiction_name: str
    violations: list[str]
    allows_nobility_arms: bool
    allows_royal_symbols: bool
    detail: str


class HeraldryExplanation(BaseModel):
    """AI explanation for heraldic validation.

    Always includes:
    - confidence: deterministic numeric score (0..1)
    - sources: Source rows referenced/available for this explanation
    - rules_applied: machine-readable rule context used to generate the explanation
    """

    summary: str
    detailed_reasoning: str
    citations: list[dict]

    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    sources: list[SourceReference] = Field(default_factory=list)
    rules_applied: dict[str, Any] = Field(default_factory=dict)


class FullValidationResponse(BaseModel):
    """Complete heraldic validation response."""
    parsed_blazon: ParsedBlazonResponse
    rule_validation: ValidationResultResponse
    jurisdiction_compliance: JurisdictionComplianceResponse | None
    svg: str | None
    overall_valid: bool
    explanation: HeraldryExplanation
    audit_id: int
