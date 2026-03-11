"""Student repository - database operations for students."""

from typing import Any

from app.models.student import StudentCreate, StudentUpdate
from app.repositories.database import get_supabase_admin_client


class StudentRepository:
    """Repository for student CRUD operations."""

    TABLE = "students"

    @staticmethod
    def _to_db(data: dict) -> dict:
        """Map model fields to DB column names."""
        result = dict(data)
        if "class_name" in result:
            result["class"] = result.pop("class_name")
        return result

    @staticmethod
    def _from_db(row: dict) -> dict:
        """Map DB columns to model fields."""
        result = dict(row)
        if "class" in result:
            result["class_name"] = result.pop("class")
        elif "class_name" not in result:
            result["class_name"] = ""
        return result

    @staticmethod
    async def create(student_data: StudentCreate) -> dict[str, Any]:
        """Create a new student."""
        client = get_supabase_admin_client()
        data = StudentRepository._to_db(student_data.model_dump())
        result = client.table(StudentRepository.TABLE).insert(data).execute()
        if not result.data:
            raise ValueError("Failed to create student")
        return StudentRepository._from_db(result.data[0])

    @staticmethod
    async def get_by_id(student_id: str) -> dict[str, Any] | None:
        """Get student by ID."""
        client = get_supabase_admin_client()
        result = client.table(StudentRepository.TABLE).select("*").eq("id", student_id).execute()
        return StudentRepository._from_db(result.data[0]) if result.data else None

    @staticmethod
    async def get_by_email(email: str) -> dict[str, Any] | None:
        """Get student by email."""
        client = get_supabase_admin_client()
        result = client.table(StudentRepository.TABLE).select("*").eq("email", email).execute()
        return StudentRepository._from_db(result.data[0]) if result.data else None

    @staticmethod
    async def get_by_roll_number(roll_number: str) -> dict[str, Any] | None:
        """Get student by roll number."""
        client = get_supabase_admin_client()
        result = client.table(StudentRepository.TABLE).select("*").eq("roll_number", roll_number).execute()
        return StudentRepository._from_db(result.data[0]) if result.data else None

    @staticmethod
    async def get_by_name(name: str) -> dict[str, Any] | None:
        """Get student by full name (case-insensitive)."""
        if not name or not name.strip():
            return None
        client = get_supabase_admin_client()
        result = client.table(StudentRepository.TABLE).select("*").ilike("name", name.strip()).execute()
        if not result.data:
            return None
        name_lower = name.strip().lower()
        for row in result.data:
            if (row.get("name") or "").strip().lower() == name_lower:
                return StudentRepository._from_db(row)
        return None

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        """Extract digits only for comparison (handles +91, 0 prefix, etc)."""
        return "".join(c for c in (phone or "") if c.isdigit())

    @staticmethod
    async def get_by_parent_phone(parent_phone: str) -> dict[str, Any] | None:
        """Get student by parent phone (normalizes to last 10 digits for Indian numbers)."""
        digits = StudentRepository._normalize_phone(parent_phone)
        if len(digits) < 10:
            return None
        key = digits[-10:]  # Last 10 digits
        client = get_supabase_admin_client()
        result = client.table(StudentRepository.TABLE).select("*").execute()
        for row in result.data or []:
            existing = StudentRepository._normalize_phone(row.get("parent_phone") or "")
            if len(existing) >= 10 and existing[-10:] == key:
                return StudentRepository._from_db(row)
        return None

    @staticmethod
    async def get_count(class_name: str | None = None) -> int:
        """Get total student count (avoids row limit)."""
        client = get_supabase_admin_client()
        query = client.table(StudentRepository.TABLE).select("id", count="exact", head=True)
        if class_name:
            query = query.eq("class", class_name)
        result = query.execute()
        return getattr(result, "count", None) or 0

    @staticmethod
    async def get_all(class_name: str | None = None) -> list[dict[str, Any]]:
        """Get all students, optionally filtered by class."""
        client = get_supabase_admin_client()
        query = client.table(StudentRepository.TABLE).select("*")
        if class_name:
            query = query.eq("class", class_name)
        result = query.execute()
        return [StudentRepository._from_db(row) for row in (result.data or [])]

    @staticmethod
    async def update(student_id: str, update_data: StudentUpdate) -> dict[str, Any]:
        """Update a student."""
        client = get_supabase_admin_client()
        data = update_data.model_dump(exclude_unset=True, by_alias=True)
        data = StudentRepository._to_db(data)
        if not data:
            return (await StudentRepository.get_by_id(student_id)) or {}
        result = client.table(StudentRepository.TABLE).update(data).eq("id", student_id).execute()
        return StudentRepository._from_db(result.data[0]) if result.data else {}

    @staticmethod
    async def delete(student_id: str) -> bool:
        """Delete a student."""
        client = get_supabase_admin_client()
        result = client.table(StudentRepository.TABLE).delete().eq("id", student_id).execute()
        return len(result.data or []) > 0
