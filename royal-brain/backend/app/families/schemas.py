from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class FamilyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    family_type: str | None
    notes: str | None
    valid_from: date
    valid_to: date | None
    created_at: datetime
    updated_at: datetime
    source_ids: list[int]


class FamilyCreate(BaseModel):
    name: str
    family_type: str | None = None
    notes: str | None = None
    valid_from: date
    valid_to: date | None = None

    source_ids: list[int] = Field(min_length=1)


class FamilyUpdate(BaseModel):
    name: str | None = None
    family_type: str | None = None
    notes: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None

    source_ids: list[int] = Field(min_length=1)
