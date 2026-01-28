from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class HeraldicEntityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    jurisdiction_id: int | None
    blazon: str | None
    notes: str | None
    valid_from: date
    valid_to: date | None
    created_at: datetime
    updated_at: datetime
    source_ids: list[int]


class HeraldicEntityCreate(BaseModel):
    name: str
    jurisdiction_id: int | None = None
    blazon: str | None = None
    notes: str | None = None
    valid_from: date
    valid_to: date | None = None

    source_ids: list[int] = Field(min_length=1)


class HeraldicEntityUpdate(BaseModel):
    name: str | None = None
    jurisdiction_id: int | None = None
    blazon: str | None = None
    notes: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None

    source_ids: list[int] = Field(min_length=1)
