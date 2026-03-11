"""Student controller - CRUD operations."""

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile

from pydantic import BaseModel, EmailStr, Field

from app.controllers.deps import require_admin, require_teacher_or_admin
from app.models.student import StudentCreate, StudentUpdate
from app.services.student_service import StudentService

router = APIRouter(prefix="/students", tags=["Students"])

# IMPORTANT: Fixed paths (e.g. /register-with-face) must be defined BEFORE parameterized paths (/{student_id})
# to avoid 405 Method Not Allowed when POST matches the wrong route.


class StudentCreateRequest(BaseModel):
    """Request body for creating student: full name, email, class A/B, parent phone, roll number."""

    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    roll_number: str = Field(..., min_length=1, max_length=50)
    parent_phone: str = Field(..., min_length=10, max_length=15)
    class_name: str = Field(..., pattern="^(A|B)$", validation_alias="class")


@router.post("/register-with-face")
async def register_student_with_face(
    request: Request,
    name: str = Form(..., min_length=1, max_length=255),
    email: str = Form(...),
    roll_number: str = Form(..., min_length=1, max_length=50),
    parent_phone: str = Form(..., min_length=10, max_length=15),
    class_name: str = Form(..., pattern="^(A|B)$", alias="class"),
    image: UploadFile = File(...),
    current_user: dict = Depends(require_teacher_or_admin),
):
    """Create a student only if a face is detected and not duplicate. Face photo is required."""
    image_bytes = await image.read()
    if not image_bytes or len(image_bytes) < 500:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail="Invalid or empty image. Please upload a clear photo with a visible face.",
        )
    student_data = StudentCreate(
        name=name.strip(),
        email=email.strip(),
        roll_number=roll_number.strip(),
        parent_phone=parent_phone.strip(),
        class_name=class_name,
    )
    client_host = request.client.host if request.client else None
    ip = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip() or client_host
    return await StudentService.register_with_face(
        student_data,
        image_bytes,
        user_id=str(current_user.get("id", "")) if current_user else None,
        ip_address=ip,
    )


@router.post("")
async def create_student(
    body: StudentCreateRequest,
    current_user: dict = Depends(require_teacher_or_admin),
):
    """BLOCKED: Students must be created via POST /students/register-with-face with a face photo."""
    from fastapi import HTTPException
    raise HTTPException(
        status_code=403,
        detail="Student creation requires face registration. Use POST /students/register-with-face with a face photo.",
    )


@router.get("")
async def list_students(
    class_name: str | None = Query(None, alias="class"),
    current_user: dict = Depends(require_teacher_or_admin),
):
    """List all students, optionally filtered by class A or B."""
    return await StudentService.list_students(class_name)


@router.get("/{student_id}")
async def get_student(
    student_id: str,
    current_user: dict = Depends(require_teacher_or_admin),
):
    """Get student by ID."""
    return await StudentService.get_student(student_id)


@router.patch("/{student_id}")
async def update_student(
    student_id: str,
    update_data: StudentUpdate,
    current_user: dict = Depends(require_admin),
):
    """Update a student (admin only)."""
    return await StudentService.update_student(student_id, update_data)


@router.delete("/{student_id}")
async def delete_student(
    student_id: str,
    current_user: dict = Depends(require_admin),
):
    """Delete a student (admin only)."""
    await StudentService.delete_student(student_id)
    return {"message": "Student deleted"}
