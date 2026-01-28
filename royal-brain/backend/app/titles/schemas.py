from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class TitleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    rank: str | None
    granted_date: date | None
    grantor_person_id: int | None
    jurisdiction_id: int | None
    notes: str | None
    valid_from: date
    valid_to: date | None
    created_at: datetime
    updated_at: datetime
    source_ids: list[int]


class TitleCreate(BaseModel):
    name: str
    rank: str | None = None
    granted_date: date | None = None
    grantor_person_id: int | None = None
    jurisdiction_id: int | None = None
    notes: str | None = None
    valid_from: date
    valid_to: date | None = None

    source_ids: list[int] = Field(min_length=1)


class TitleUpdate(BaseModel):
    name: str | None = None
    rank: str | None = None
    granted_date: date | None = None
    grantor_person_id: int | None = None
    jurisdiction_id: int | None = None
    notes: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None

    source_ids: list[int] = Field(min_length=1)
