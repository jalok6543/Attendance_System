"""Log repository - audit trail and system logs."""

from typing import Any

from app.repositories.database import get_supabase_admin_client


class LogRepository:
    """Repository for audit logs."""

    TABLE = "logs"

    @staticmethod
    async def create(
        user_id: str | None,
        action: str,
        ip_address: str | None = None,
        device_info: str | None = None,
        details: dict | None = None,
    ) -> dict[str, Any]:
        """Create audit log entry."""
        client = get_supabase_admin_client()
        data = {
            "user_id": user_id if user_id else None,
            "action": action,
            "ip_address": ip_address,
            "device_info": device_info or "",
            "details": details or {},
        }
        result = client.table(LogRepository.TABLE).insert(data).execute()
        return result.data[0] if result.data else {}

    @staticmethod
    async def get_recent(limit: int = 100) -> list[dict[str, Any]]:
        """Get recent log entries."""
        client = get_supabase_admin_client()
        result = (
            client.table(LogRepository.TABLE)
            .select("*")
            .order("timestamp", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []
