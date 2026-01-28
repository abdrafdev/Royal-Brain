from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class PersonName(BaseModel):
    name: str
    valid_from: date
    valid_to: date | None = None
    name_type: str | None = None


class PersonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    primary_name: str
    sex: str | None
    names: list[PersonName] | None
    birth_date: date | None
    death_date: date | None
    notes: str | None
    valid_from: date
    valid_to: date | None
    created_at: datetime
    updated_at: datetime
    source_ids: list[int]


class PersonCreate(BaseModel):
    primary_name: str
    sex: str | None = Field(default=None, max_length=16)
    names: list[PersonName] | None = None
    birth_date: date | None = None
    death_date: date | None = None
    notes: str | None = None
    valid_from: date
    valid_to: date | None = None

    source_ids: list[int] = Field(min_length=1)


class PersonUpdate(BaseModel):
    primary_name: str | None = None
    sex: str | None = Field(default=None, max_length=16)
    names: list[PersonName] | None = None
    birth_date: date | None = None
    death_date: date | None = None
    notes: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None

    source_ids: list[int] = Field(min_length=1)
