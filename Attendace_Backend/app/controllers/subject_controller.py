"""Subject controller - CRUD operations."""

from fastapi import APIRouter, Depends

from app.controllers.deps import require_teacher_or_admin
from app.models.subject import SubjectCreate, SubjectUpdate
from app.repositories.subject_repository import SubjectRepository

router = APIRouter(prefix="/subjects", tags=["Subjects"])


@router.post("")
async def create_subject(
    body: SubjectCreate,
    current_user: dict = Depends(require_teacher_or_admin),
):
    """Create a new subject."""
    return await SubjectRepository.create(body)


@router.get("")
async def list_subjects(current_user: dict = Depends(require_teacher_or_admin)):
    """List all subjects."""
    return await SubjectRepository.get_all()


@router.get("/{subject_id}")
async def get_subject(
    subject_id: str,
    current_user: dict = Depends(require_teacher_or_admin),
):
    """Get subject by ID."""
    sub = await SubjectRepository.get_by_id(subject_id)
    if not sub:
        from fastapi import HTTPException
        raise HTTPException(404, "Subject not found")
    return sub
