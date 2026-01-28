from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    jurisdiction_id: int | None
    classification: str | None
    legitimacy_score: int | None
    fons_honorum_person_id: int | None
    fraud_flags: list[str] | None
    recognized_by: list[str] | None
    founding_document_source_id: int | None
    last_legitimacy_check: datetime | None
    granted_date: date | None
    grantor_person_id: int | None
    notes: str | None
    valid_from: date
    valid_to: date | None
    created_at: datetime
    updated_at: datetime
    source_ids: list[int]


class OrderCreate(BaseModel):
    name: str
    jurisdiction_id: int | None = None
    classification: str | None = None
    fons_honorum_person_id: int | None = None
    founding_document_source_id: int | None = None
    granted_date: date | None = None
    grantor_person_id: int | None = None
    notes: str | None = None
    valid_from: date
    valid_to: date | None = None

    source_ids: list[int] = Field(min_length=1)


class OrderUpdate(BaseModel):
    name: str | None = None
    jurisdiction_id: int | None = None
    classification: str | None = None
    fons_honorum_person_id: int | None = None
    founding_document_source_id: int | None = None
    granted_date: date | None = None
    grantor_person_id: int | None = None
    notes: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None

    source_ids: list[int] = Field(min_length=1)
