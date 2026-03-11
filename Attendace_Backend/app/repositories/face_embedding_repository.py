"""Face embedding repository - database operations for face embeddings."""

from typing import Any

from app.repositories.database import get_supabase_admin_client


class FaceEmbeddingRepository:
    """Repository for face embedding operations."""

    TABLE = "face_embeddings"

    @staticmethod
    async def create(student_id: str, embedding_vector: list[float]) -> dict[str, Any]:
        """Store face embedding for a student."""
        client = get_supabase_admin_client()
        data = {"student_id": student_id, "embedding_vector": embedding_vector}
        result = client.table(FaceEmbeddingRepository.TABLE).insert(data).execute()
        if not result.data:
            raise ValueError("Failed to store embedding")
        return result.data[0]

    @staticmethod
    async def get_by_student(student_id: str) -> list[dict[str, Any]]:
        """Get all embeddings for a student."""
        client = get_supabase_admin_client()
        result = (
            client.table(FaceEmbeddingRepository.TABLE)
            .select("*")
            .eq("student_id", student_id)
            .execute()
        )
        return result.data or []

    @staticmethod
    async def get_all_embeddings() -> list[dict[str, Any]]:
        """Get all embeddings for recognition (student_id, embedding_vector)."""
        client = get_supabase_admin_client()
        result = client.table(FaceEmbeddingRepository.TABLE).select("id, student_id, embedding_vector").execute()
        return result.data or []

    @staticmethod
    async def delete_by_student(student_id: str) -> bool:
        """Delete all embeddings for a student."""
        client = get_supabase_admin_client()
        result = client.table(FaceEmbeddingRepository.TABLE).delete().eq("student_id", student_id).execute()
        return True
