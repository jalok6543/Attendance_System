"""Teacher controller - list teachers, ensure teacher record exists."""

from fastapi import APIRouter, Depends

from app.controllers.deps import get_current_user, require_teacher_or_admin
from app.repositories.teacher_repository import TeacherRepository

router = APIRouter(prefix="/teachers", tags=["Teachers"])


@router.get("")
async def list_teachers(current_user: dict = Depends(require_teacher_or_admin)):
    """List all teachers."""
    return await TeacherRepository.get_all()


@router.post("/ensure")
async def ensure_teacher_record(current_user: dict = Depends(get_current_user)):
    """Create teacher record for current user if they have teacher role and no record."""
    if current_user.get("role") != "teacher":
        return {"message": "User is not a teacher", "teacher": None}
    teacher = await TeacherRepository.get_or_create(current_user["sub"])
    return {"teacher": teacher}
