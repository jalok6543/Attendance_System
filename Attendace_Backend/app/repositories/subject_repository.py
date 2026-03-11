"""Subject repository - database operations for subjects."""

from typing import Any

from app.models.subject import SubjectCreate, SubjectUpdate
from app.repositories.database import get_supabase_admin_client


class SubjectRepository:
    """Repository for subject CRUD operations."""

    TABLE = "subjects"

    @staticmethod
    async def get_by_name(name: str) -> dict[str, Any] | None:
        """Get subject by name (case-insensitive). Returns None if not found."""
        if not name or not name.strip():
            return None
        client = get_supabase_admin_client()
        result = (
            client.table(SubjectRepository.TABLE)
            .select("id, name")
            .ilike("name", name.strip())
            .execute()
        )
        if not result.data or len(result.data) == 0:
            return None
        for row in result.data:
            if row.get("name", "").lower() == name.strip().lower():
                return row
        return None

    @staticmethod
    async def create(subject_data: SubjectCreate) -> dict[str, Any]:
        """Create a new subject. Raises ValueError if subject name already exists."""
        from app.core.exceptions import DuplicateError

        existing = await SubjectRepository.get_by_name(subject_data.name)
        if existing:
            raise DuplicateError(
                f'A subject named "{subject_data.name}" already exists. Please use a different name.'
            )
        try:
            client = get_supabase_admin_client()
            data = {"name": subject_data.name, "teacher_id": subject_data.teacher_id}
            result = client.table(SubjectRepository.TABLE).insert(data).execute()
            if not result.data:
                raise ValueError("Failed to create subject")
            return result.data[0]
        except Exception as e:
            if "foreign key" in str(e).lower() or "teacher" in str(e).lower():
                raise ValueError("Invalid teacher. Ensure a teacher account exists.") from e
            raise ValueError(f"Failed to create subject: {e}") from e

    @staticmethod
    async def get_by_id(subject_id: str) -> dict[str, Any] | None:
        """Get subject by ID."""
        client = get_supabase_admin_client()
        result = (
            client.table(SubjectRepository.TABLE)
            .select("*, teachers(*, users(name))")
            .eq("id", subject_id)
            .execute()
        )
        if not result.data:
            return None
        row = result.data[0]
        if row.get("teachers") and row["teachers"].get("users"):
            row["teacher_name"] = row["teachers"]["users"].get("name")
            del row["teachers"]
        return row

    @staticmethod
    async def get_by_teacher(teacher_id: str) -> list[dict[str, Any]]:
        """Get all subjects for a teacher."""
        client = get_supabase_admin_client()
        result = client.table(SubjectRepository.TABLE).select("*").eq("teacher_id", teacher_id).execute()
        return result.data or []

    @staticmethod
    async def get_all() -> list[dict[str, Any]]:
        """Get all subjects."""
        client = get_supabase_admin_client()
        result = client.table(SubjectRepository.TABLE).select("*").execute()
        return result.data or []

    @staticmethod
    async def update(subject_id: str, update_data: SubjectUpdate) -> dict[str, Any]:
        """Update a subject."""
        client = get_supabase_admin_client()
        data = update_data.model_dump(exclude_unset=True)
        if not data:
            return (await SubjectRepository.get_by_id(subject_id)) or {}
        result = client.table(SubjectRepository.TABLE).update(data).eq("id", subject_id).execute()
        return result.data[0] if result.data else {}
