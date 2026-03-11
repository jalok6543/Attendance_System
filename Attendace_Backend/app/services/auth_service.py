"""Authentication service - login, JWT, session management."""

from fastapi import Request

from app.core.exceptions import AuthenticationError
from app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)
from app.models.user import TokenResponse, UserCreate, UserLogin, UserResponse, UserRole
from app.repositories.log_repository import LogRepository
from app.repositories.user_repository import UserRepository
from app.core.config import get_settings


class AuthService:
    """Service for authentication operations."""

    @staticmethod
    async def login(credentials: UserLogin, request: Request | None = None) -> TokenResponse:
        """Authenticate user and return JWT token."""
        user_data = await UserRepository.get_by_email_with_password(credentials.email)
        if not user_data:
            raise AuthenticationError("Invalid email or password")

        if not verify_password(credentials.password, user_data["password_hash"]):
            raise AuthenticationError("Invalid email or password")

        if user_data["role"] == UserRole.STUDENT.value:
            raise AuthenticationError("Students cannot login. Attendance is marked by teachers.")

        user = UserResponse(
            id=str(user_data["id"]),
            name=user_data["name"],
            email=user_data["email"],
            role=UserRole(user_data["role"]),
            created_at=user_data.get("created_at"),
        )

        settings = get_settings()
        access_token = create_access_token(
            data={"sub": str(user_data["id"]), "role": user_data["role"], "email": user_data["email"]}
        )

        # Log login
        if request:
            await LogRepository.create(
                user_id=str(user_data["id"]),
                action="login",
                ip_address=request.client.host if request.client else None,
                device_info=request.headers.get("user-agent"),
            )

        return TokenResponse(
            access_token=access_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user,
        )

    @staticmethod
    async def register(user_data: UserCreate, role: UserRole = UserRole.STUDENT) -> UserResponse:
        """Register a new user."""
        existing = await UserRepository.get_by_email(user_data.email)
        if existing:
            raise AuthenticationError("Email already registered")

        password_hash = get_password_hash(user_data.password)
        create_data = user_data.model_dump()
        create_data["role"] = role
        created = await UserRepository.create(
            UserCreate(**create_data),
            password_hash,
        )
        return UserResponse(
            id=str(created["id"]),
            name=created["name"],
            email=created["email"],
            role=UserRole(created["role"]),
            created_at=created.get("created_at"),
        )

    @staticmethod
    async def reset_admin_password() -> None:
        """Reset all seed user passwords to Password123! (dev only)."""
        from app.core.security import get_password_hash
        from app.repositories.database import get_supabase_admin_client
        client = get_supabase_admin_client()
        hash = get_password_hash("Password123!")
        for email in ("admin@school.com", "teacher@school.com"):
            client.table("users").update({"password_hash": hash}).eq("email", email).execute()

    @staticmethod
    def get_current_user_from_token(token: str) -> dict | None:
        """Extract and validate user from JWT token."""
        payload = decode_access_token(token)
        return payload
