"""Student service - business logic for student operations."""

from typing import Any

from app.core.exceptions import DuplicateError, DuplicateFaceError, FaceRecognitionError, NotFoundError
from app.models.student import StudentCreate, StudentUpdate
from app.repositories.face_embedding_repository import FaceEmbeddingRepository
from app.repositories.log_repository import LogRepository
from app.repositories.student_repository import StudentRepository


class StudentService:
    """Service for student operations. Teacher or Admin can add. Only Admin can delete."""

    @staticmethod
    async def create_student(student_data: StudentCreate) -> dict[str, Any]:
        """Create a new student. DISABLED: Students must be created via register-with-face only."""
        from app.core.exceptions import AppException
        raise AppException(
            "Student creation requires face registration. Use POST /students/register-with-face with a face photo.",
            status_code=400,
        )

    @staticmethod
    async def register_with_face(
        student_data: StudentCreate,
        image_bytes: bytes,
        user_id: str | None = None,
        ip_address: str | None = None,
    ) -> dict[str, Any]:
        """Create student only if face is detected and NOT a duplicate. Requires face photo."""
        from app.core.config import get_settings
        from app.services.face_recognition_service import FaceRecognitionService

        settings = get_settings()
        engine = FaceRecognitionService.get_engine()

        embedding = FaceRecognitionService.extract_embedding_for_enrollment(image_bytes)
        if embedding is None:
            raise FaceRecognitionError(
                "No face detected. A clear, front-facing face must be visible in the image. Student cannot be added without a registered face."
            )

        # STEP 1: Duplicate face check - reject if same face exists anywhere in database
        stored = await FaceEmbeddingRepository.get_all_embeddings()
        if stored:
            stored_list = [(str(r["student_id"]), r["embedding_vector"]) for r in stored]
            duplicate = engine.find_duplicate_face(
                embedding,
                stored_list,
                threshold=settings.ENROLLMENT_DUPLICATE_THRESHOLD,
            )
            if duplicate:
                matched_student_id, similarity = duplicate
                await LogRepository.create(
                    user_id or None,
                    "duplicate_face_attempt",
                    ip_address=ip_address,
                    details={
                        "attempted_name": student_data.name,
                        "attempted_email": student_data.email,
                        "matched_student_id": matched_student_id,
                        "similarity": round(similarity, 4),
                    },
                )
                raise DuplicateFaceError(
                    "This face is already registered in the system. Each student must have a unique face.",
                    similarity=similarity,
                )

        # STEP 2: Duplicate name - reject if same full name exists
        existing_name = await StudentRepository.get_by_name(student_data.name)
        if existing_name:
            raise DuplicateError(
                f'A student with the name "{student_data.name}" already exists. Use a different name.'
            )

        # STEP 3: Duplicate parent phone - reject if same number exists
        existing_phone = await StudentRepository.get_by_parent_phone(student_data.parent_phone)
        if existing_phone:
            raise DuplicateError(
                "A student with this parent phone number already exists. Each parent number must be unique."
            )

        # STEP 4: Duplicate email and roll number
        existing_email = await StudentRepository.get_by_email(student_data.email)
        if existing_email:
            raise DuplicateError("Email already registered for a student")
        existing_roll = await StudentRepository.get_by_roll_number(student_data.roll_number)
        if existing_roll:
            raise DuplicateError("Roll number already exists")

        student = await StudentRepository.create(student_data)
        try:
            await FaceEmbeddingRepository.create(str(student["id"]), embedding.tolist())
            from app.services.face_recognition_service import refresh_embedding_cache
            await refresh_embedding_cache()
        except Exception as e:
            await StudentRepository.delete(str(student["id"]))
            raise FaceRecognitionError(
                "Failed to save face data. Student was not added. Please try again with a clear, front-facing face photo."
            ) from e
        return student

    @staticmethod
    async def get_student(student_id: str) -> dict[str, Any]:
        """Get student by ID."""
        student = await StudentRepository.get_by_id(student_id)
        if not student:
            raise NotFoundError("Student not found")
        return student

    @staticmethod
    async def list_students(class_name: str | None = None) -> list[dict[str, Any]]:
        """List all students, optionally filtered by class."""
        return await StudentRepository.get_all(class_name)

    @staticmethod
    async def update_student(student_id: str, update_data: StudentUpdate) -> dict[str, Any]:
        """Update a student (admin only)."""
        student = await StudentService.get_student(student_id)
        data = update_data.model_dump(exclude_unset=True)

        if "email" in data:
            existing = await StudentRepository.get_by_email(data["email"])
            if existing and str(existing.get("id")) != str(student_id):
                raise DuplicateError("Email already registered for a student")
        if "roll_number" in data:
            existing = await StudentRepository.get_by_roll_number(data["roll_number"])
            if existing and str(existing.get("id")) != str(student_id):
                raise DuplicateError("Roll number already exists")

        if data:
            await StudentRepository.update(student_id, StudentUpdate(**data))
        return await StudentService.get_student(student_id)

    @staticmethod
    async def delete_student(student_id: str) -> bool:
        """Delete a student (admin only)."""
        await StudentService.get_student(student_id)
        await StudentRepository.delete(student_id)
        return True
