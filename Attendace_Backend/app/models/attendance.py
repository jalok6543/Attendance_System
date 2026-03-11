"""Attendance model and schemas."""

from datetime import date, datetime, time
from enum import Enum

from pydantic import Field

from app.models.base import BaseSchema


class AttendanceStatus(str, Enum):
    """Attendance status enumeration."""

    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"
    EXCUSED = "excused"


class AttendanceBase(BaseSchema):
    """Base attendance schema."""

    student_id: str
    subject_id: str
    date: date
    status: AttendanceStatus = AttendanceStatus.PRESENT
    confidence_score: float | None = Field(None, ge=0, le=1)


class AttendanceCreate(AttendanceBase):
    """Schema for creating attendance record."""

    check_in: time | None = None
    check_out: time | None = None
    ip_address: str | None = None
    device_info: str | None = None


class AttendanceUpdate(BaseSchema):
    """Schema for updating attendance."""

    check_out: time | None = None
    status: AttendanceStatus | None = None


class AttendanceResponse(AttendanceBase):
    """Schema for attendance response."""

    id: str
    check_in: time | None = None
    check_out: time | None = None
    ip_address: str | None = None
    device_info: str | None = None
    created_at: datetime | None = None


class AttendanceSummary(BaseSchema):
    """Schema for attendance summary."""

    student_id: str
    subject_id: str
    total_classes: int
    present_count: int
    absent_count: int
    percentage: float
