"""Attendance repository - database operations for attendance records."""

import calendar
from datetime import date, timedelta
from typing import Any

from app.core.config import get_settings
from app.models.attendance import AttendanceCreate, AttendanceStatus
from app.repositories.database import get_supabase_admin_client


class AttendanceRepository:
    """Repository for attendance CRUD operations."""

    TABLE = "attendance"

    @staticmethod
    async def create(attendance_data: AttendanceCreate) -> dict[str, Any]:
        """Create attendance record."""
        client = get_supabase_admin_client()
        data = {
            "student_id": attendance_data.student_id,
            "subject_id": attendance_data.subject_id,
            "date": attendance_data.date.isoformat(),
            "status": attendance_data.status.value,
            "confidence_score": attendance_data.confidence_score,
            "check_in": attendance_data.check_in.isoformat() if attendance_data.check_in else None,
            "check_out": attendance_data.check_out.isoformat() if attendance_data.check_out else None,
            "ip_address": attendance_data.ip_address,
            "device_info": attendance_data.device_info,
        }
        result = client.table(AttendanceRepository.TABLE).insert(data).execute()
        if not result.data:
            raise ValueError("Failed to create attendance")
        return result.data[0]

    @staticmethod
    async def get_by_student_date_subject(
        student_id: str, subject_id: str, attendance_date: date
    ) -> dict[str, Any] | None:
        """Check if attendance already exists for student/subject/date."""
        client = get_supabase_admin_client()
        result = (
            client.table(AttendanceRepository.TABLE)
            .select("*")
            .eq("student_id", student_id)
            .eq("subject_id", subject_id)
            .eq("date", attendance_date.isoformat())
            .execute()
        )
        return result.data[0] if result.data else None

    @staticmethod
    async def update(attendance_id: str, data: dict) -> dict[str, Any]:
        """Update attendance record."""
        client = get_supabase_admin_client()
        result = client.table(AttendanceRepository.TABLE).update(data).eq("id", attendance_id).execute()
        return result.data[0] if result.data else {}

    @staticmethod
    async def update_check_out(attendance_id: str, check_out: str) -> dict[str, Any]:
        """Update check_out time for attendance record."""
        client = get_supabase_admin_client()
        result = (
            client.table(AttendanceRepository.TABLE)
            .update({"check_out": check_out})
            .eq("id", attendance_id)
            .execute()
        )
        return result.data[0] if result.data else {}

    @staticmethod
    async def get_by_id(attendance_id: str) -> dict[str, Any] | None:
        """Get attendance by ID."""
        client = get_supabase_admin_client()
        result = client.table(AttendanceRepository.TABLE).select("*").eq("id", attendance_id).execute()
        return result.data[0] if result.data else None

    @staticmethod
    async def get_by_student(
        student_id: str,
        subject_id: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """Get attendance records for a student."""
        client = get_supabase_admin_client()
        query = client.table(AttendanceRepository.TABLE).select("*").eq("student_id", student_id)
        if subject_id:
            query = query.eq("subject_id", subject_id)
        if start_date:
            query = query.gte("date", start_date.isoformat())
        if end_date:
            query = query.lte("date", end_date.isoformat())
        result = query.order("date", desc=True).execute()
        return result.data or []

    @staticmethod
    async def get_overall_summary(student_id: str) -> dict[str, Any]:
        """Get overall attendance summary for a student (all subjects)."""
        records = await AttendanceRepository.get_by_student(student_id)
        total = len(records)
        present = sum(1 for r in records if r.get("status") == AttendanceStatus.PRESENT.value)
        percentage = (present / total * 100) if total > 0 else 0
        return {"student_id": student_id, "total": total, "present": present, "percentage": int(round(percentage, 0))}

    @staticmethod
    async def get_monthly_summary(student_id: str, year: int, month: int) -> dict[str, Any]:
        """Get attendance summary for a student for a specific month.
        Uses working days (Mon-Fri) in the month. Present = distinct dates with attendance.
        """
        first_day = date(year, month, 1)
        last_day = date(year, month, calendar.monthrange(year, month)[1])
        records = await AttendanceRepository.get_by_student(
            student_id, start_date=first_day, end_date=last_day
        )
        present_dates = set()
        for r in records:
            if r.get("status") == AttendanceStatus.PRESENT.value and r.get("date"):
                d = r["date"] if isinstance(r["date"], str) else r["date"]
                present_dates.add(d[:10] if isinstance(d, str) else str(d))
        present_days = len(present_dates)
        working_days = sum(
            1 for d in range(1, last_day.day + 1)
            if date(year, month, d).weekday() < 5
        )
        percentage = int(round((present_days / working_days * 100), 0)) if working_days > 0 else 0
        return {
            "student_id": student_id,
            "present_days": present_days,
            "working_days": working_days,
            "percentage": percentage,
        }

    @staticmethod
    async def get_summary(student_id: str, subject_id: str) -> dict[str, Any]:
        """Get attendance summary for student in subject."""
        records = await AttendanceRepository.get_by_student(student_id, subject_id)
        total = len(records)
        present = sum(1 for r in records if r.get("status") == AttendanceStatus.PRESENT.value)
        absent = total - present
        percentage = (present / total * 100) if total > 0 else 0
        return {
            "student_id": student_id,
            "subject_id": subject_id,
            "total_classes": total,
            "present_count": present,
            "absent_count": absent,
            "percentage": int(round(percentage, 0)),
        }

    @staticmethod
    async def get_daily_report(subject_id: str, report_date: date) -> list[dict[str, Any]]:
        """Get daily attendance report for a subject."""
        client = get_supabase_admin_client()
        result = (
            client.table(AttendanceRepository.TABLE)
            .select("*, students(name, roll_number, parent_phone)")
            .eq("subject_id", subject_id)
            .eq("date", report_date.isoformat())
            .execute()
        )
        return result.data or []

    @staticmethod
    async def get_dashboard_stats(report_date: date) -> dict[str, Any]:
        """Get dashboard stats: today's attendance count, active sessions, monthly rate."""
        client = get_supabase_admin_client()
        today_str = report_date.isoformat()

        # Today's attendance records
        result = (
            client.table(AttendanceRepository.TABLE)
            .select("student_id, subject_id")
            .eq("date", today_str)
            .eq("status", AttendanceStatus.PRESENT.value)
            .execute()
        )
        records = result.data or []
        today_student_ids = {r["student_id"] for r in records}
        today_subject_ids = {r["subject_id"] for r in records}

        # This month's attendance for rate calculation
        first_day = date(report_date.year, report_date.month, 1)
        last_day = date(report_date.year, report_date.month, calendar.monthrange(report_date.year, report_date.month)[1])
        month_result = (
            client.table(AttendanceRepository.TABLE)
            .select("student_id, date, status")
            .gte("date", first_day.isoformat())
            .lte("date", last_day.isoformat())
            .execute()
        )
        month_records = month_result.data or []
        present_dates = set()
        for r in month_records:
            if r.get("status") == AttendanceStatus.PRESENT.value and r.get("date"):
                d = r["date"] if isinstance(r["date"], str) else r["date"]
                present_dates.add((r["student_id"], d[:10] if isinstance(d, str) else str(d)))
        present_count = len(present_dates)
        working_days = sum(
            1 for d in range(1, last_day.day + 1)
            if date(report_date.year, report_date.month, d).weekday() < 5
        )

        return {
            "today_count": len(today_student_ids),
            "active_sessions": len(today_subject_ids),
            "present_this_month": present_count,
            "working_days_this_month": working_days,
        }

    @staticmethod
    async def get_analytics_by_date_range(
        start_date: date, end_date: date, subject_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Get attendance records in date range for analytics aggregation. Optional subject filter."""
        client = get_supabase_admin_client()
        query = (
            client.table(AttendanceRepository.TABLE)
            .select("student_id, subject_id, date, status")
            .gte("date", start_date.isoformat())
            .lte("date", end_date.isoformat())
        )
        if subject_id:
            query = query.eq("subject_id", subject_id)
        result = query.execute()
        return result.data or []

    @staticmethod
    async def get_attendance_report_by_date_range(
        start_date: date, end_date: date, subject_id: str | None = None, expected_classes: int | None = None, threshold: float | None = None
    ) -> list[dict[str, Any]]:
        """Get per-student attendance report. If subject_id: filter by subject. Else: all subjects.
        Returns: roll_no, student_name, class, subject, total_classes, present, absent, attendance_percent, status.
        Status: Low if < threshold, High if >= threshold.
        """
        client = get_supabase_admin_client()
        query = (
            client.table(AttendanceRepository.TABLE)
            .select("student_id, subject_id, date, status")
            .gte("date", start_date.isoformat())
            .lte("date", end_date.isoformat())
        )
        if subject_id:
            query = query.eq("subject_id", subject_id)
        result = query.execute()
        raw = result.data or []

        # Determine total_classes: use expected_classes if provided, else infer from actual dates
        if expected_classes is not None and expected_classes > 0:
            total_classes = expected_classes
        else:
            # Infer total class sessions from actual attendance records (dates present in database).
            # This avoids assuming 5 classes per week when only 1 session has happened.
            class_dates: set[str] = set()
            for r in raw:
                if not r.get("date"):
                    continue
                dt = r["date"][:10] if isinstance(r["date"], str) else str(r["date"])[:10]
                class_dates.add(dt)
            total_classes = max(1, len(class_dates))

        students_result = client.table("students").select("id, name, roll_number, class").execute()
        students_map = {s["id"]: s for s in (students_result.data or [])}
        subjects_result = client.table("subjects").select("id, name").execute()
        subjects_map = {s["id"]: s for s in (subjects_result.data or [])}

        by_student: dict[str, set[str]] = {}
        for r in raw:
            if r.get("status") != AttendanceStatus.PRESENT.value:
                continue
            sid = r["student_id"]
            dt = r["date"][:10] if isinstance(r["date"], str) else str(r["date"])[:10]
            if sid not in by_student:
                by_student[sid] = set()
            by_student[sid].add(dt)

        subject_label = subjects_map.get(subject_id, {}).get("name", "All") if subject_id else "All"

        threshold_value = threshold if threshold is not None else get_settings().DEFAULT_ATTENDANCE_THRESHOLD

        report = []
        for student_id, present_dates in by_student.items():
            student = students_map.get(student_id, {})
            present = len(present_dates)
            absent = max(0, total_classes - present)
            pct = int(round((present / total_classes * 100), 0)) if total_classes > 0 else 0
            status = "High" if pct >= threshold_value else "Low"
            report.append({
                "roll_no": student.get("roll_number", ""),
                "student_name": student.get("name", ""),
                "class": student.get("class", ""),
                "subject": subject_label,
                "total_classes": total_classes,
                "present": present,
                "absent": absent,
                "attendance_percent": f"{pct}%",
                "status": status,
            })
        report.sort(key=lambda x: (x["class"], x["roll_no"]))
        return report
