from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class JurisdictionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str | None
    legal_system: str | None
    nobility_abolished_date: date | None
    succession_rules_json: dict | None
    recognized_orders: list[str] | None
    legal_references: list[str] | None

    jurisdiction_type: str | None
    parent_id: int | None
    notes: str | None
    valid_from: date
    valid_to: date | None
    created_at: datetime
    updated_at: datetime
    source_ids: list[int]


class JurisdictionCreate(BaseModel):
    name: str
    code: str | None = Field(default=None, max_length=8)
    legal_system: str | None = None
    nobility_abolished_date: date | None = None
    succession_rules_json: dict | None = None
    recognized_orders: list[str] | None = None
    legal_references: list[str] | None = None

    jurisdiction_type: str | None = None
    parent_id: int | None = None
    notes: str | None = None
    valid_from: date
    valid_to: date | None = None

    source_ids: list[int] = Field(min_length=1)


class JurisdictionUpdate(BaseModel):
    name: str | None = None
    code: str | None = Field(default=None, max_length=8)
    legal_system: str | None = None
    nobility_abolished_date: date | None = None
    succession_rules_json: dict | None = None
    recognized_orders: list[str] | None = None
    legal_references: list[str] | None = None

    jurisdiction_type: str | None = None
    parent_id: int | None = None
    notes: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None

    source_ids: list[int] = Field(min_length=1)
