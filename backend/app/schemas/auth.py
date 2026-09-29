"""Pydantic schemas for authentication and user management."""

from datetime import datetime

from pydantic import BaseModel, Field

# Pattern that accepts standard emails including internal/demo TLDs like .local
EMAIL_REGEX = r"^[\w\.\+\-]+@[\w\-]+(\.[\w\-]+)+$"


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class LoginRequest(BaseModel):
    email: str = Field(..., pattern=EMAIL_REGEX)
    password: str = Field(min_length=1)


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
