from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class SourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_type: str
    jurisdiction_id: int | None
    issued_date: date | None
    citation: str
    url: str | None
    notes: str | None
    valid_from: date
    valid_to: date | None
    created_at: datetime
    updated_at: datetime


class SourceCreate(BaseModel):
    source_type: str
    jurisdiction_id: int | None = None
    issued_date: date | None = None
    citation: str
    url: str | None = None
    notes: str | None = None
    valid_from: date
    valid_to: date | None = None


class SourceUpdate(BaseModel):
    source_type: str | None = None
    jurisdiction_id: int | None = None
    issued_date: date | None = None
    citation: str | None = None
    url: str | None = None
    notes: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None
