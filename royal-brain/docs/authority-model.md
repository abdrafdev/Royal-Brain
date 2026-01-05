# Royal BrAIn™ — Authority Model (Day 1)
## Principle
Authority is explicit. Decisions are hierarchical. Not every actor is permitted to assert or modify historical identity.

## Roles
- `ADMIN`: system authority (may create users, assign roles, view full audit log)
- `RESEARCHER`: may create/submit analytical inputs (future engines)
- `VIEWER`: read-only access

## Enforcement
Backend enforces role checks through dependency guards (RBAC). Endpoints that mutate state require elevated authority.

## Auditability
Authority-bearing actions must emit audit events capturing:
- who acted
- what action occurred
- which entity was affected
- when it occurred
- a deterministic event hash (future trust layer anchoring)
