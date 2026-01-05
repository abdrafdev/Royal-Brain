from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, status

from app.auth.dependencies import get_current_user
from app.roles.enums import Role
from app.users.models import User


ROLE_RANK: dict[Role, int] = {
    Role.VIEWER: 10,
    Role.RESEARCHER: 50,
    Role.ADMIN: 100,
}


def require_roles(*allowed: Role) -> Callable[[User], User]:
    """Dependency guard enforcing that the current user has one of the allowed roles."""

    def _guard(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient authority for this operation.",
            )
        return user

    return _guard
