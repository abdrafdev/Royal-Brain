from __future__ import annotations

import re
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


def normalize_relationship_type(value: str) -> str:
    """Normalize relationship types to a canonical, engine-compatible form.

    Canonical format: lowercase snake_case (e.g. parent_child, adoption, marriage).
    """
    v = (value or "").strip()
    v = v.replace("-", "_").replace(" ", "_")
    v = re.sub(r"_+", "_", v)
    return v.lower()


ALLOWED_ENTITY_TYPES = {
    "person",
    "family",
    "jurisdiction",
    "order",
    "title",
    "heraldic_entity",
}


class RelationshipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    relationship_type: str

    left_entity_type: str
    left_entity_id: int

    right_entity_type: str
    right_entity_id: int

    notes: str | None

    valid_from: date
    valid_to: date | None

    created_at: datetime
    updated_at: datetime

    source_ids: list[int]


class RelationshipCreate(BaseModel):
    relationship_type: str

    @field_validator("relationship_type", mode="before")
    @classmethod
    def _normalize_relationship_type(cls, v):
        if isinstance(v, str):
            return normalize_relationship_type(v)
        return v

    left_entity_type: str
    left_entity_id: int

    right_entity_type: str
    right_entity_id: int

    notes: str | None = None

    valid_from: date
    valid_to: date | None = None

    source_ids: list[int] = Field(min_length=1)


class RelationshipUpdate(BaseModel):
    relationship_type: str | None = None

    @field_validator("relationship_type", mode="before")
    @classmethod
    def _normalize_relationship_type(cls, v):
        if v is None:
            return v
        if isinstance(v, str):
            return normalize_relationship_type(v)
        return v

    left_entity_type: str | None = None
    left_entity_id: int | None = None

    right_entity_type: str | None = None
    right_entity_id: int | None = None

    notes: str | None = None

    valid_from: date | None = None
    valid_to: date | None = None

    source_ids: list[int] = Field(min_length=1)
