"""Student model and schemas."""

from pydantic import EmailStr, Field

from app.models.base import BaseSchema


class StudentBase(BaseSchema):
    """Base student schema."""

    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    roll_number: str = Field(..., min_length=1, max_length=50)
    parent_phone: str = Field(..., min_length=10, max_length=15)
    class_name: str = Field(..., pattern="^(A|B)$", description="Class A or B")


class StudentCreate(StudentBase):
    """Schema for creating a student (no password)."""

    pass


class StudentUpdate(BaseSchema):
    """Schema for updating a student."""

    name: str | None = Field(None, min_length=1, max_length=255)
    email: EmailStr | None = None
    roll_number: str | None = Field(None, min_length=1, max_length=50)
    parent_phone: str | None = Field(None, min_length=10, max_length=15)
    class_name: str | None = Field(None, pattern="^(A|B)$", validation_alias="class")


class StudentResponse(StudentBase):
    """Schema for student response."""

    id: str
