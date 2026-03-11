"""Dependency injection for controllers."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.security import decode_access_token
from app.models.user import UserRole

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> dict:
    """Extract and validate current user from JWT."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return payload


async def require_admin(
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    """Require admin role."""
    if current_user.get("role") != UserRole.ADMIN.value:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


async def require_teacher_or_admin(
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    """Require teacher or admin role."""
    role = current_user.get("role")
    if role not in (UserRole.TEACHER.value, UserRole.ADMIN.value):
        raise HTTPException(status_code=403, detail="Teacher or admin access required")
    return current_user


async def require_student(
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    """Require student role."""
    if current_user.get("role") != UserRole.STUDENT.value:
        raise HTTPException(status_code=403, detail="Student access required")
    return current_user
