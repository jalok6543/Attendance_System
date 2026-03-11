"""Subject model and schemas."""

from pydantic import Field

from app.models.base import BaseSchema


class SubjectBase(BaseSchema):
    """Base subject schema."""

    name: str = Field(..., min_length=1, max_length=255)
    teacher_id: str


class SubjectCreate(SubjectBase):
    """Schema for creating a subject."""

    pass


class SubjectUpdate(BaseSchema):
    """Schema for updating a subject."""

    name: str | None = Field(None, min_length=1, max_length=255)
    teacher_id: str | None = None


class SubjectResponse(SubjectBase):
    """Schema for subject response."""

    id: str
    teacher_name: str | None = None
