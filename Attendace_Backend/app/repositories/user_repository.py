"""User repository - database operations for users."""

from typing import Any

from app.core.exceptions import NotFoundError
from app.models.user import UserCreate, UserResponse, UserRole
from app.repositories.database import get_supabase_admin_client


class UserRepository:
    """Repository for user CRUD operations."""

    TABLE = "users"

    @staticmethod
    async def create(user_data: UserCreate, password_hash: str) -> dict[str, Any]:
        """Create a new user."""
        client = get_supabase_admin_client()
        data = {
            "name": user_data.name,
            "email": user_data.email,
            "role": user_data.role.value,
            "password_hash": password_hash,
        }
        result = client.table(UserRepository.TABLE).insert(data).execute()
        if not result.data:
            raise ValueError("Failed to create user")
        return result.data[0]

    @staticmethod
    async def get_by_id(user_id: str) -> dict[str, Any] | None:
        """Get user by ID."""
        client = get_supabase_admin_client()
        result = client.table(UserRepository.TABLE).select("*").eq("id", user_id).execute()
        return result.data[0] if result.data else None

    @staticmethod
    async def get_by_email(email: str) -> dict[str, Any] | None:
        """Get user by email."""
        client = get_supabase_admin_client()
        result = client.table(UserRepository.TABLE).select("*").eq("email", email).execute()
        return result.data[0] if result.data else None

    @staticmethod
    async def get_by_email_with_password(email: str) -> dict[str, Any] | None:
        """Get user by email including password hash."""
        client = get_supabase_admin_client()
        result = (
            client.table(UserRepository.TABLE)
            .select("*, password_hash")
            .eq("email", email)
            .execute()
        )
        return result.data[0] if result.data else None

    @staticmethod
    async def update(user_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update user."""
        client = get_supabase_admin_client()
        result = client.table(UserRepository.TABLE).update(data).eq("id", user_id).execute()
        return result.data[0] if result.data else {}

    @staticmethod
    async def delete(user_id: str) -> bool:
        """Delete user."""
        client = get_supabase_admin_client()
        result = client.table(UserRepository.TABLE).delete().eq("id", user_id).execute()
        return True

    @staticmethod
    async def get_all(role: UserRole | None = None) -> list[dict[str, Any]]:
        """Get all users, optionally filtered by role."""
        client = get_supabase_admin_client()
        query = client.table(UserRepository.TABLE).select("*")
        if role:
            query = query.eq("role", role.value)
        result = query.execute()
        return result.data or []
