"""Face recognition controller - capture, verify, register embeddings."""

from fastapi import APIRouter, Depends, File, UploadFile

from app.controllers.deps import get_current_user, require_teacher_or_admin
from app.services.face_recognition_service import FaceRecognitionService

router = APIRouter(prefix="/face", tags=["Face Recognition"])


@router.post("/register/{student_id}")
async def register_face(
    student_id: str,
    image: UploadFile = File(...),
    current_user: dict = Depends(require_teacher_or_admin),
):
    """Register face embedding for a student."""
    image_bytes = await image.read()
    return await FaceRecognitionService.register_face(student_id, image_bytes)


@router.post("/verify")
async def verify_face(
    image: UploadFile = File(...),
    subject_id: str | None = None,
    current_user: dict = Depends(require_teacher_or_admin),
):
    """Verify face and return matched student with confidence."""
    image_bytes = await image.read()
    return await FaceRecognitionService.verify_face(image_bytes, subject_id)


@router.post("/verify-multi")
async def verify_faces_multi(
    image: UploadFile = File(...),
    subject_id: str | None = None,
    current_user: dict = Depends(require_teacher_or_admin),
):
    """Detect up to 3 faces, match each using cached embeddings (real-time optimized)."""
    image_bytes = await image.read()
    return await FaceRecognitionService.verify_faces_multi(image_bytes, subject_id)


@router.post("/verify-multi-stable")
async def verify_faces_multi_stable(
    image1: UploadFile = File(..., alias="image1"),
    image2: UploadFile = File(..., alias="image2"),
    image3: UploadFile = File(..., alias="image3"),
    subject_id: str | None = None,
    current_user: dict = Depends(require_teacher_or_admin),
):
    """3-frame stability: average embeddings from 3 frames, then match. Reduces false positives."""
    frames = [await image1.read(), await image2.read(), await image3.read()]
    return await FaceRecognitionService.verify_faces_multi_stable(frames, subject_id)


@router.post("/verify-liveness")
async def verify_face_with_liveness(
    image: UploadFile = File(...),
    subject_id: str | None = None,
    current_user: dict = Depends(get_current_user),
):
    """Verify face with liveness detection (blink/head movement)."""
    image_bytes = await image.read()
    return await FaceRecognitionService.verify_face_with_liveness(image_bytes, subject_id)
