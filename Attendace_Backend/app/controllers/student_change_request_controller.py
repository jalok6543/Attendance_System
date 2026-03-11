"""Student change request controller - teachers request, admins approve."""

from fastapi import APIRouter, Depends, Query

from pydantic import BaseModel, Field

from app.controllers.deps import get_current_user, require_admin, require_teacher_or_admin
from app.services.student_change_request_service import StudentChangeRequestService

router = APIRouter(prefix="/student-change-requests", tags=["Student Change Requests"])


class CreateRequestBody(BaseModel):
    """Request body for creating a change request."""

    student_id: str = Field(..., min_length=32, max_length=36)
    proposed_changes: dict = Field(default_factory=dict, description="Optional structured changes; message-only is allowed")
    message: str = Field(..., min_length=1, max_length=500, description="Reason/description of changes - required")


@router.post("")
async def create_request(
    body: CreateRequestBody,
    current_user: dict = Depends(require_teacher_or_admin),
):
    """Teacher submits a change request for a student. Admin will review."""
    if current_user.get("role") == "admin":
        from fastapi import HTTPException
        raise HTTPException(
            status_code=403,
            detail="Admins can edit directly. Use the Students page to make changes.",
        )
    return await StudentChangeRequestService.create_request(
        student_id=body.student_id,
        user_id=str(current_user.get("sub", "")),
        proposed_changes=body.proposed_changes,
        message=body.message,
    )


@router.get("")
async def list_requests(
    status: str | None = Query(None, description="Filter: pending, approved, rejected"),
    current_user: dict = Depends(get_current_user),
):
    """List change requests. Admin sees all; Teacher sees own."""
    if current_user.get("role") == "admin":
        return await StudentChangeRequestService.list_for_admin(status)
    return await StudentChangeRequestService.list_for_teacher(str(current_user.get("sub", "")))


@router.get("/pending-count")
async def get_pending_count(current_user: dict = Depends(get_current_user)):
    """Get count of pending requests (for admin notification badge)."""
    if current_user.get("role") != "admin":
        return {"count": 0}
    count = await StudentChangeRequestService.count_pending()
    return {"count": count}


@router.get("/{request_id}")
async def get_request(
    request_id: str,
    current_user: dict = Depends(require_teacher_or_admin),
):
    """Get a single change request."""
    return await StudentChangeRequestService.get_request(request_id)


@router.post("/{request_id}/approve")
async def approve_request(
    request_id: str,
    current_user: dict = Depends(require_admin),
):
    """Admin approves request and applies changes to student."""
    return await StudentChangeRequestService.approve(
        request_id, str(current_user.get("sub", ""))
    )


@router.post("/{request_id}/reject")
async def reject_request(
    request_id: str,
    current_user: dict = Depends(require_admin),
):
    """Admin rejects request."""
    return await StudentChangeRequestService.reject(
        request_id, str(current_user.get("sub", ""))
    )
