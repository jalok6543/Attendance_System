"""Attendance controller - check-in, check-out, reports."""

from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from app.controllers.deps import get_current_user, require_teacher_or_admin
from app.models.attendance import AttendanceStatus
from app.services.attendance_service import AttendanceService

router = APIRouter(prefix="/attendance", tags=["Attendance"])


class CheckInRequest(BaseModel):
    student_id: str = Field(..., min_length=32, max_length=36)
    subject_id: str = Field(..., min_length=32, max_length=36)
    confidence_score: float = Field(1.0, ge=0, le=1)


@router.post("/check-in")
async def mark_check_in(
    body: CheckInRequest,
    request: Request,
    current_user: dict = Depends(require_teacher_or_admin),
):
    """Mark attendance check-in. Auto-called when face is recognized."""
    return await AttendanceService.mark_check_in(
        body.student_id, body.subject_id, body.confidence_score, current_user["sub"], request
    )


@router.get("/dashboard-stats")
async def get_dashboard_stats(
    report_date: date | None = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """Get dashboard stats: today's attendance, total students, attendance rate, active sessions."""
    return await AttendanceService.get_dashboard_stats(report_date)


@router.get("/analytics-chart")
async def get_analytics_chart(
    start_date: date | None = Query(None, description="Start date for chart range"),
    end_date: date | None = Query(None, description="End date for chart range"),
    subject_id: str | None = Query(None, description="Filter by subject (optional)"),
    current_user: dict = Depends(get_current_user),
):
    """Get attendance analytics chart data for dashboard (date range). Optional subject filter."""
    return await AttendanceService.get_attendance_analytics(start_date, end_date, subject_id)


@router.get("/attendance-report")
async def get_attendance_report(
    start_date: date | None = Query(None, description="Start date for report"),
    end_date: date | None = Query(None, description="End date for report"),
    subject_id: str | None = Query(None, description="Filter by subject (optional, all if not set)"),
    current_user: dict = Depends(get_current_user),
):
    """Get per-student attendance report for Excel export. If no subject: export all subjects."""
    return await AttendanceService.get_attendance_report(start_date, end_date, subject_id)


@router.post("/check-out")
async def mark_check_out(
    request: Request,
    student_id: str = Query(..., min_length=32, max_length=36),
    subject_id: str = Query(..., min_length=32, max_length=36),
    current_user: dict = Depends(require_teacher_or_admin),
):
    """Mark attendance check-out."""
    return await AttendanceService.mark_check_out(
        student_id, subject_id, current_user["sub"], request
    )


@router.get("/student/{student_id}")
async def get_student_attendance(
    student_id: str,
    subject_id: str | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """Get attendance records for a student."""
    return await AttendanceService.get_student_attendance(
        student_id, subject_id, start_date, end_date
    )


@router.get("/summary/{student_id}/{subject_id}")
async def get_attendance_summary(
    student_id: str,
    subject_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get attendance percentage summary."""
    return await AttendanceService.get_attendance_summary(student_id, subject_id)


@router.get("/daily-report")
async def get_daily_report(
    subject_id: str,
    report_date: date = Query(...),
    current_user: dict = Depends(require_teacher_or_admin),
):
    """Get daily attendance report for a subject."""
    return await AttendanceService.get_daily_report(subject_id, report_date)


@router.get("/low-attendance-preview")
async def get_low_attendance_preview(
    year: int | None = Query(None, description="Year (default: current)"),
    month: int | None = Query(None, description="Month 1-12 (default: current)"),
    current_user: dict = Depends(require_teacher_or_admin),
):
    """Preview students with low attendance (<60%) for a given month. No SMS sent."""
    return await AttendanceService.get_low_attendance_preview(year=year, month=month)


@router.post("/send-low-attendance-alerts")
async def send_low_attendance_alerts_manual(
    year: int | None = Query(None, description="Year (default: current)"),
    month: int | None = Query(None, description="Month 1-12 (default: current)"),
    current_user: dict = Depends(require_teacher_or_admin),
):
    """Manually send SMS to parents of students with attendance below 60% for the given month."""
    return await AttendanceService.send_low_attendance_alerts(year=year, month=month)


@router.post("/manual-override")
async def manual_override(
    student_id: str,
    subject_id: str,
    attendance_date: date,
    status: AttendanceStatus,
    current_user: dict = Depends(require_teacher_or_admin),
):
    """Teacher manual override for attendance."""
    return await AttendanceService.manual_override(
        student_id, subject_id, attendance_date, status, current_user["sub"]
    )
