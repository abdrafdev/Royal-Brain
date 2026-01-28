from __future__ import annotations

from collections import defaultdict
from datetime import date

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.genealogy.schemas import (
    Direction,
    GenealogyCheckResponse,
    GenealogyEdge,
    GenealogyIssue,
    GenealogyPersonNode,
    GenealogyTreeResponse,
    TreeLevel,
)
from app.persons.models import Person
from app.relationships.models import Relationship

PARENT_CHILD_TYPES = {"parent_child", "adoption"}
MARRIAGE_TYPE = "marriage"


def _is_valid_as_of(*, valid_from: date, valid_to: date | None, as_of: date | None) -> bool:
    if as_of is None:
        return True
    if valid_from > as_of:
        return False
    if valid_to is None:
        return True
    return valid_to >= as_of


def _relationship_as_of_clause(as_of: date | None):
    if as_of is None:
        return None
    return and_(Relationship.valid_from <= as_of, or_(Relationship.valid_to.is_(None), Relationship.valid_to >= as_of))


def _tree_levels_from_edges(root_id: int, edges: list[GenealogyEdge], *, mode: Direction) -> list[TreeLevel]:
    # mode controls traversal direction for parent-child/adoption edges:
    # - ancestors: traverse child -> parent (reverse)
    # - descendants: traverse parent -> child
    # Edges in list may include marriage; those are ignored.

    parent_to_children: dict[int, list[int]] = defaultdict(list)
    child_to_parents: dict[int, list[int]] = defaultdict(list)

    for e in edges:
        if e.relationship_type not in PARENT_CHILD_TYPES:
            continue
        parent_to_children[e.from_person_id].append(e.to_person_id)
        child_to_parents[e.to_person_id].append(e.from_person_id)

    levels: list[TreeLevel] = [TreeLevel(level=0, person_ids=[root_id])]
    seen: set[int] = {root_id}

    frontier = [root_id]
    level = 0

    while frontier:
        next_frontier: list[int] = []
        level += 1

        for pid in frontier:
            neighbors = child_to_parents[pid] if mode == "ancestors" else parent_to_children[pid]
            for nid in neighbors:
                if nid in seen:
                    continue
                seen.add(nid)
                next_frontier.append(nid)

        if not next_frontier:
            break

        levels.append(TreeLevel(level=level, person_ids=sorted(next_frontier)))
        frontier = next_frontier

    return levels


def build_person_tree(
    db: Session,
    *,
    root_person_id: int,
    direction: Direction,
    depth: int,
    as_of: date | None,
    include_marriages: bool,
) -> GenealogyTreeResponse:
    root = db.get(Person, root_person_id)
    if root is None:
        raise ValueError("Person not found")

    # Traverse only parent-child/adoption edges to collect lineage persons.
    collected_person_ids: set[int] = {root_person_id}
    collected_relationships: dict[int, Relationship] = {}

    frontier = {root_person_id}
    for _level in range(depth):
        if not frontier:
            break

        newly_found: set[int] = set()

        clauses = [
            Relationship.left_entity_type == "person",
            Relationship.right_entity_type == "person",
            Relationship.relationship_type.in_(sorted(PARENT_CHILD_TYPES)),
        ]
        as_of_clause = _relationship_as_of_clause(as_of)
        if as_of_clause is not None:
            clauses.append(as_of_clause)

        if direction in ("ancestors", "both"):
            q = select(Relationship).where(*clauses, Relationship.right_entity_id.in_(sorted(frontier)))
            rows = db.scalars(q).all()
            for r in rows:
                collected_relationships[r.id] = r
                if r.left_entity_id not in collected_person_ids:
                    newly_found.add(r.left_entity_id)

        if direction in ("descendants", "both"):
            q = select(Relationship).where(*clauses, Relationship.left_entity_id.in_(sorted(frontier)))
            rows = db.scalars(q).all()
            for r in rows:
                collected_relationships[r.id] = r
                if r.right_entity_id not in collected_person_ids:
                    newly_found.add(r.right_entity_id)

        collected_person_ids.update(newly_found)
        frontier = newly_found

    # Optionally attach marriages for discovered persons (adds spouse nodes but does not expand lineage).
    if include_marriages and collected_person_ids:
        clauses = [
            Relationship.left_entity_type == "person",
            Relationship.right_entity_type == "person",
            Relationship.relationship_type == MARRIAGE_TYPE,
        ]
        as_of_clause = _relationship_as_of_clause(as_of)
        if as_of_clause is not None:
            clauses.append(as_of_clause)

        q = select(Relationship).where(
            *clauses,
            or_(
                Relationship.left_entity_id.in_(sorted(collected_person_ids)),
                Relationship.right_entity_id.in_(sorted(collected_person_ids)),
            ),
        )
        for r in db.scalars(q).all():
            collected_relationships[r.id] = r
            collected_person_ids.add(r.left_entity_id)
            collected_person_ids.add(r.right_entity_id)

    # Load person records.
    people = db.scalars(select(Person).where(Person.id.in_(sorted(collected_person_ids)))).all()
    people_by_id = {p.id: p for p in people}

    nodes: list[GenealogyPersonNode] = []
    for pid in sorted(collected_person_ids):
        p = people_by_id.get(pid)
        if p is None:
            # Should not happen due to FK-less relationship endpoints, but keep safe.
            continue
        nodes.append(
            GenealogyPersonNode(
                id=p.id,
                primary_name=p.primary_name,
                birth_date=p.birth_date,
                death_date=p.death_date,
            )
        )

    edges: list[GenealogyEdge] = []
    for r in collected_relationships.values():
        if r.left_entity_type != "person" or r.right_entity_type != "person":
            continue
        if not _is_valid_as_of(valid_from=r.valid_from, valid_to=r.valid_to, as_of=as_of):
            continue

        edges.append(
            GenealogyEdge(
                id=r.id,
                relationship_type=r.relationship_type,
                from_person_id=r.left_entity_id,
                to_person_id=r.right_entity_id,
                valid_from=r.valid_from,
                valid_to=r.valid_to,
                source_ids=r.source_ids,
            )
        )

    edges.sort(key=lambda e: e.id)

    levels_ancestors = None
    levels_descendants = None
    if direction in ("ancestors", "both"):
        levels_ancestors = _tree_levels_from_edges(root_person_id, edges, mode="ancestors")
        # Trim to requested depth (level 0 + depth generations)
        levels_ancestors = levels_ancestors[: depth + 1]

    if direction in ("descendants", "both"):
        levels_descendants = _tree_levels_from_edges(root_person_id, edges, mode="descendants")
        levels_descendants = levels_descendants[: depth + 1]

    return GenealogyTreeResponse(
        root_person_id=root_person_id,
        direction=direction,
        depth=depth,
        nodes=nodes,
        edges=edges,
        levels_ancestors=levels_ancestors,
        levels_descendants=levels_descendants,
    )


def check_timeline_consistency(
    db: Session,
    *,
    root_person_id: int,
    depth: int,
    as_of: date | None,
) -> GenealogyCheckResponse:
    # Reuse tree builder to collect the relevant nodes/edges.
    tree = build_person_tree(
        db,
        root_person_id=root_person_id,
        direction="both",
        depth=depth,
        as_of=as_of,
        include_marriages=True,
    )

    issues: list[GenealogyIssue] = []

    people_by_id = {n.id: n for n in tree.nodes}

    # Person sanity.
    for p in tree.nodes:
        if p.birth_date and p.death_date and p.birth_date > p.death_date:
            issues.append(
                GenealogyIssue(
                    severity="error",
                    code="PERSON_BIRTH_AFTER_DEATH",
                    message="Person birth_date is after death_date.",
                    person_id=p.id,
                )
            )

    # Relationship sanity.
    for e in tree.edges:
        if e.valid_to is not None and e.valid_to < e.valid_from:
            issues.append(
                GenealogyIssue(
                    severity="error",
                    code="REL_VALID_TO_BEFORE_VALID_FROM",
                    message="Relationship valid_to is before valid_from.",
                    relationship_id=e.id,
                )
            )

        left = people_by_id.get(e.from_person_id)
        right = people_by_id.get(e.to_person_id)

        # Timeline checks require person nodes.
        if left is None or right is None:
            continue

        if e.relationship_type in PARENT_CHILD_TYPES:
            parent = left
            child = right

            if parent.birth_date and child.birth_date and parent.birth_date > child.birth_date:
                issues.append(
                    GenealogyIssue(
                        severity="error",
                        code="PARENT_BORN_AFTER_CHILD",
                        message="Parent birth_date is after child birth_date.",
                        relationship_id=e.id,
                    )
                )

            if parent.death_date and child.birth_date and parent.death_date < child.birth_date:
                issues.append(
                    GenealogyIssue(
                        severity="error",
                        code="PARENT_DIED_BEFORE_CHILD_BIRTH",
                        message="Parent death_date is before child birth_date.",
                        relationship_id=e.id,
                    )
                )

            if child.birth_date and e.valid_from < child.birth_date:
                issues.append(
                    GenealogyIssue(
                        severity="warning",
                        code="REL_START_BEFORE_CHILD_BIRTH",
                        message="Relationship valid_from is before child birth_date (may indicate wrong dates or direction).",
                        relationship_id=e.id,
                    )
                )

        elif e.relationship_type == MARRIAGE_TYPE:
            spouse_a = left
            spouse_b = right

            if spouse_a.birth_date and e.valid_from < spouse_a.birth_date:
                issues.append(
                    GenealogyIssue(
                        severity="error",
                        code="MARRIAGE_BEFORE_SPOUSE_A_BIRTH",
                        message="Marriage valid_from is before spouse A birth_date.",
                        relationship_id=e.id,
                    )
                )

            if spouse_b.birth_date and e.valid_from < spouse_b.birth_date:
                issues.append(
                    GenealogyIssue(
                        severity="error",
                        code="MARRIAGE_BEFORE_SPOUSE_B_BIRTH",
                        message="Marriage valid_from is before spouse B birth_date.",
                        relationship_id=e.id,
                    )
                )

            if spouse_a.death_date and e.valid_from > spouse_a.death_date:
                issues.append(
                    GenealogyIssue(
                        severity="error",
                        code="MARRIAGE_AFTER_SPOUSE_A_DEATH",
                        message="Marriage valid_from is after spouse A death_date.",
                        relationship_id=e.id,
                    )
                )

            if spouse_b.death_date and e.valid_from > spouse_b.death_date:
                issues.append(
                    GenealogyIssue(
                        severity="error",
                        code="MARRIAGE_AFTER_SPOUSE_B_DEATH",
                        message="Marriage valid_from is after spouse B death_date.",
                        relationship_id=e.id,
                    )
                )

    # Cycle detection on parent-child/adoption edges.
    graph: dict[int, list[int]] = defaultdict(list)
    for e in tree.edges:
        if e.relationship_type in PARENT_CHILD_TYPES:
            graph[e.from_person_id].append(e.to_person_id)

    # DFS cycle detection.
    visiting: set[int] = set()
    visited: set[int] = set()

    def _dfs(node: int) -> bool:
        visiting.add(node)
        for nxt in graph.get(node, []):
            if nxt in visiting:
                return True
            if nxt in visited:
                continue
            if _dfs(nxt):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    for n in graph.keys():
        if n in visited:
            continue
        if _dfs(n):
            issues.append(
                GenealogyIssue(
                    severity="error",
                    code="ANCESTRY_CYCLE_DETECTED",
                    message="Cycle detected in parent-child/adoption graph.",
                    person_id=n,
                )
            )
            break

    return GenealogyCheckResponse(root_person_id=root_person_id, depth=depth, issues=issues)
