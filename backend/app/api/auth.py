"""Authentication endpoints: login, refresh, me."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.rbac import get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.db import get_db
from app.models.entities import User
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse, UserResponse
from app.services.audit.service import AuditService

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    access_token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})
    refresh_token = create_refresh_token({"sub": user.id})

    # Log successful login to tamper-evident audit log
    AuditService.record(
        db=db,
        actor=user.email,
        action="AUTH_LOGIN",
        entity_type="user",
        entity_id=user.id,
        payload={"role": user.role},
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(payload: RefreshRequest, db: Session = Depends(get_db)):
    try:
        claims = decode_token(payload.refresh_token)
        if claims.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type: expected refresh token",
            )
        user_id = claims.get("sub")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user = db.scalar(select(User).where(User.id == user_id, User.is_active.is_(True)))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or deactivated",
        )

    access_token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})
    new_refresh_token = create_refresh_token({"sub": user.id})

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.ACCESS_TOKEN_MINUTES * 60,
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
