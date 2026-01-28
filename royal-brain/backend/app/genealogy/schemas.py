from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


Direction = Literal["ancestors", "descendants", "both"]


class GenealogyPersonNode(BaseModel):
    id: int
    primary_name: str
    birth_date: date | None
    death_date: date | None


class GenealogyEdge(BaseModel):
    id: int
    relationship_type: str

    from_person_id: int
    to_person_id: int

    valid_from: date
    valid_to: date | None

    source_ids: list[int]


class TreeLevel(BaseModel):
    level: int
    person_ids: list[int]


class GenealogyTreeResponse(BaseModel):
    root_person_id: int
    direction: Direction
    depth: int = Field(ge=1, le=10)

    nodes: list[GenealogyPersonNode]
    edges: list[GenealogyEdge]

    # Breadth levels (root is level=0). These levels are computed using parent-child/adoption edges only.
    levels_ancestors: list[TreeLevel] | None = None
    levels_descendants: list[TreeLevel] | None = None


Severity = Literal["error", "warning"]


class GenealogyIssue(BaseModel):
    severity: Severity
    code: str
    message: str

    person_id: int | None = None
    relationship_id: int | None = None


class GenealogyCheckResponse(BaseModel):
    root_person_id: int
    depth: int = Field(ge=1, le=10)
    issues: list[GenealogyIssue]
