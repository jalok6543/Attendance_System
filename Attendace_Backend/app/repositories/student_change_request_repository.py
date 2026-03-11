"""Student change request repository - database operations."""

from typing import Any

from app.repositories.database import get_supabase_admin_client


class StudentChangeRequestRepository:
    """Repository for student change request operations."""

    TABLE = "student_change_requests"

    @staticmethod
    async def create(
        student_id: str,
        requested_by: str,
        proposed_changes: dict,
        message: str,
    ) -> dict[str, Any]:
        """Create a change request."""
        client = get_supabase_admin_client()
        data = {
            "student_id": student_id,
            "requested_by": requested_by,
            "proposed_changes": proposed_changes,
            "message": message.strip(),
            "status": "pending",
        }
        result = client.table(StudentChangeRequestRepository.TABLE).insert(data).execute()
        if not result.data:
            raise ValueError("Failed to create change request")
        return result.data[0]

    @staticmethod
    async def get_by_id(request_id: str) -> dict[str, Any] | None:
        """Get a change request by ID."""
        client = get_supabase_admin_client()
        result = (
            client.table(StudentChangeRequestRepository.TABLE)
            .select("*, students(id, name, email, roll_number, parent_phone, class), users!requested_by(id, name, email)")
            .eq("id", request_id)
            .execute()
        )
        return result.data[0] if result.data else None

    @staticmethod
    async def list_all(status: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
        """List all change requests (admin). Optional status filter. Limited for performance."""
        client = get_supabase_admin_client()
        query = (
            client.table(StudentChangeRequestRepository.TABLE)
            .select("id, student_id, requested_by, proposed_changes, message, status, created_at, students(id, name, email, roll_number, parent_phone, class), users!requested_by(id, name, email)")
            .order("created_at", desc=True)
            .limit(limit)
        )
        if status:
            query = query.eq("status", status)
        result = query.execute()
        return result.data or []

    @staticmethod
    async def list_by_requested_by(user_id: str, limit: int = 100) -> list[dict[str, Any]]:
        """List change requests made by a specific user (teacher). Limited for performance."""
        client = get_supabase_admin_client()
        result = (
            client.table(StudentChangeRequestRepository.TABLE)
            .select("id, student_id, requested_by, proposed_changes, message, status, created_at, students(id, name, email, roll_number, parent_phone, class)")
            .eq("requested_by", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []

    @staticmethod
    async def count_pending() -> int:
        """Count pending requests (for admin notification badge)."""
        client = get_supabase_admin_client()
        result = (
            client.table(StudentChangeRequestRepository.TABLE)
            .select("id", count="exact")
            .eq("status", "pending")
            .execute()
        )
        count = getattr(result, "count", None)
        if count is not None:
            return int(count)
        return len(result.data or [])

    @staticmethod
    async def update_status(
        request_id: str,
        status: str,
        reviewed_by: str,
    ) -> dict[str, Any]:
        """Update request status (approve/reject)."""
        from datetime import datetime

        client = get_supabase_admin_client()
        data = {
            "status": status,
            "reviewed_by": reviewed_by,
            "reviewed_at": datetime.utcnow().isoformat(),
        }
        result = (
            client.table(StudentChangeRequestRepository.TABLE)
            .update(data)
            .eq("id", request_id)
            .execute()
        )
        return result.data[0] if result.data else {}
