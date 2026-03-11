"""Teacher repository - database operations for teachers."""

from typing import Any

from app.repositories.database import get_supabase_admin_client


class TeacherRepository:
    """Repository for teacher CRUD operations."""

    TABLE = "teachers"

    @staticmethod
    async def get_by_user_id(user_id: str) -> dict[str, Any] | None:
        """Get teacher by user ID."""
        client = get_supabase_admin_client()
        result = client.table(TeacherRepository.TABLE).select("*").eq("user_id", user_id).execute()
        return result.data[0] if result.data else None

    @staticmethod
    async def create(user_id: str) -> dict[str, Any]:
        """Create teacher record for user."""
        client = get_supabase_admin_client()
        result = client.table(TeacherRepository.TABLE).insert({"user_id": user_id}).execute()
        if not result.data:
            raise ValueError("Failed to create teacher")
        return result.data[0]

    @staticmethod
    async def get_or_create(user_id: str) -> dict[str, Any]:
        """Get teacher by user_id, create if not exists."""
        teacher = await TeacherRepository.get_by_user_id(user_id)
        if teacher:
            return teacher
        return await TeacherRepository.create(user_id)

    @staticmethod
    async def get_all() -> list[dict[str, Any]]:
        """Get all teachers with user info."""
        client = get_supabase_admin_client()
        result = client.table(TeacherRepository.TABLE).select("*, users(id, name, email)").execute()
        return result.data or []
