"""Student change request service - business logic."""

from typing import Any

from app.core.exceptions import NotFoundError, ValidationError
from app.models.student import StudentUpdate
from app.repositories.student_repository import StudentRepository
from app.repositories.teacher_repository import TeacherRepository
from app.repositories.student_change_request_repository import StudentChangeRequestRepository
from app.services.student_service import StudentService


class StudentChangeRequestService:
    """Service for student change requests."""

    @staticmethod
    async def create_request(
        student_id: str,
        user_id: str,
        proposed_changes: dict,
        message: str,
    ) -> dict[str, Any]:
        """Teacher creates a change request. Only teachers can create (not admins)."""
        teacher = await TeacherRepository.get_by_user_id(user_id)
        if not teacher:
            raise NotFoundError("Teacher record not found")

        student = await StudentRepository.get_by_id(student_id)
        if not student:
            raise NotFoundError("Student not found")

        if not message or not str(message).strip():
            raise ValidationError("Message to Admin is required. Please describe the changes you need.")

        allowed_keys = {"name", "email", "roll_number", "parent_phone", "class"}
        filtered = {k: v for k, v in (proposed_changes or {}).items() if k in allowed_keys and v is not None and str(v).strip()}

        return await StudentChangeRequestRepository.create(
            student_id=student_id,
            requested_by=user_id,
            proposed_changes=filtered or {},
            message=message,
        )

    @staticmethod
    async def list_for_admin(status: str | None = None) -> list[dict[str, Any]]:
        """Admin lists all requests."""
        return await StudentChangeRequestRepository.list_all(status)

    @staticmethod
    async def list_for_teacher(user_id: str) -> list[dict[str, Any]]:
        """Teacher lists their own requests."""
        return await StudentChangeRequestRepository.list_by_requested_by(user_id)

    @staticmethod
    async def get_request(request_id: str) -> dict[str, Any]:
        """Get a single request."""
        req = await StudentChangeRequestRepository.get_by_id(request_id)
        if not req:
            raise NotFoundError("Change request not found")
        return req

    @staticmethod
    async def count_pending() -> int:
        """Count pending requests for admin badge."""
        return await StudentChangeRequestRepository.count_pending()

    @staticmethod
    async def approve(request_id: str, admin_user_id: str) -> dict[str, Any]:
        """Admin approves request and applies changes to student."""
        req = await StudentChangeRequestRepository.get_by_id(request_id)
        if not req:
            raise NotFoundError("Change request not found")
        if req.get("status") != "pending":
            raise ValidationError("Request has already been processed")

        changes = req.get("proposed_changes", {})
        student_id = req["student_id"]

        update_data = {}
        if "name" in changes:
            update_data["name"] = str(changes["name"]).strip()
        if "email" in changes:
            update_data["email"] = str(changes["email"]).strip()
        if "roll_number" in changes:
            update_data["roll_number"] = str(changes["roll_number"]).strip()
        if "parent_phone" in changes:
            update_data["parent_phone"] = str(changes["parent_phone"]).strip()
        if "class" in changes:
            update_data["class_name"] = str(changes["class"]).strip()

        if update_data:
            await StudentService.update_student(student_id, StudentUpdate(**update_data))

        await StudentChangeRequestRepository.update_status(request_id, "approved", admin_user_id)
        return await StudentChangeRequestRepository.get_by_id(request_id) or req

    @staticmethod
    async def reject(request_id: str, admin_user_id: str) -> dict[str, Any]:
        """Admin rejects request."""
        req = await StudentChangeRequestRepository.get_by_id(request_id)
        if not req:
            raise NotFoundError("Change request not found")
        if req.get("status") != "pending":
            raise ValidationError("Request has already been processed")

        await StudentChangeRequestRepository.update_status(request_id, "rejected", admin_user_id)
        return await StudentChangeRequestRepository.get_by_id(request_id) or req
