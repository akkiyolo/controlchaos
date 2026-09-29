"""Role-Based Access Control (RBAC) and authentication dependencies."""

from enum import Enum
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db import get_db
from app.models.entities import User

security_scheme = HTTPBearer(auto_error=False)


class Role(str, Enum):
    ADMIN = "admin"
    CONTROL_OWNER = "control_owner"
    REVIEWER = "reviewer"
    ANALYST = "analyst"
    AUDITOR = "auditor"


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Dependency that extracts, verifies the JWT bearer token, and loads active User."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type: expected access token",
            )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token claims: missing subject",
            )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {str(exc)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.scalar(select(User).where(User.id == user_id, User.is_active.is_(True)))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or account is deactivated",
        )
    return user


def require_roles(*allowed_roles: str):
    """
    Dependency factory to enforce required roles.
    Admins are always granted access.
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role == Role.ADMIN.value:
            return current_user

        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted for role '{current_user.role}'. Required: {allowed_roles}",
            )
        return current_user

    return role_checker


def assert_maker_checker(maker_id: str, checker_id: str) -> None:
    """Enforces server-side maker-checker rule: maker cannot approve their own change."""
    if maker_id == checker_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maker-checker violation: the maker cannot approve or check their own proposal/change",
        )
