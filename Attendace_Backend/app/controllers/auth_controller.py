"""Authentication controller - login, register."""

from fastapi import APIRouter, Depends, Request

from app.controllers.deps import get_current_user
from app.core.config import get_settings
from app.models.user import TokenResponse, UserCreate, UserLogin
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, request: Request):
    """Authenticate user and return JWT token."""
    return await AuthService.login(credentials, request)


@router.get("/reset-admin-password")
async def reset_admin_password():
    """Dev only: Reset admin@school.com password to Password123!"""
    if get_settings().ENVIRONMENT == "production":
        from fastapi import HTTPException
        raise HTTPException(403, "Not available in production")
    await AuthService.reset_admin_password()
    return {"message": "Password reset. Use admin@school.com / Password123!"}


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user."""
    return {"user": current_user}
