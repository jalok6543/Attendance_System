"""User model and schemas."""

from datetime import datetime
from enum import Enum

from pydantic import EmailStr, Field

from app.models.base import BaseSchema


class UserRole(str, Enum):
    """User role enumeration."""

    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"


class UserBase(BaseSchema):
    """Base user schema."""

    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    role: UserRole


class UserCreate(UserBase):
    """Schema for creating a user."""

    password: str = Field(..., min_length=8, max_length=128)


class UserUpdate(BaseSchema):
    """Schema for updating a user."""

    name: str | None = Field(None, min_length=1, max_length=255)
    email: EmailStr | None = None
    password: str | None = Field(None, min_length=8, max_length=128)


class UserResponse(UserBase):
    """Schema for user response (excludes password)."""

    id: str
    created_at: datetime | None = None


class UserLogin(BaseSchema):
    """Schema for login request."""

    email: EmailStr
    password: str


class TokenResponse(BaseSchema):
    """Schema for JWT token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
