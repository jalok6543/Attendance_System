"""Face-related request/response schemas."""

from pydantic import BaseModel, Field


class FaceRegisterRequest(BaseModel):
    """Request for face registration."""

    student_id: str


class FaceVerifyResponse(BaseModel):
    """Response for face verification."""

    matched: bool
    student_id: str | None = None
    confidence: float | None = None
