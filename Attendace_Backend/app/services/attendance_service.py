"""Attendance service - business logic for attendance operations."""

import time
from datetime import date, datetime, timedelta
from typing import Any

from fastapi import Request

from app.core.config import get_settings
from app.core.exceptions import DuplicateError, NotFoundError
from app.models.attendance import AttendanceCreate, AttendanceStatus
from app.repositories.attendance_repository import AttendanceRepository
from app.repositories.log_repository import LogRepository
from app.repositories.student_repository import StudentRepository
from app.repositories.subject_repository import SubjectRepository
from app.services.sms_service import SMSService


def _is_duplicate_error(exc: BaseException) -> bool:
    """Check if exception is due to unique constraint violation."""
    msg = str(exc).lower()
    return (
        "duplicate" in msg
        or "unique" in msg
        or "23505" in msg  # PostgreSQL unique_violation
        or "already exists" in msg
    )


# In-memory cache: (student_id, subject_id, date_str) -> timestamp
# Prevents rapid duplicate API calls from camera loop within 60 seconds
_RECENT_CHECKIN_CACHE: dict[tuple[str, str, str], float] = {}
_RECENT_CHECKIN_TTL_SEC = 60


def _was_recently_marked(student_id: str, subject_id: str, dt: date) -> bool:
    """Check if this student/subject/date was marked in the last TTL seconds."""
    key = (student_id, subject_id, dt.isoformat())
    now = time.monotonic()
    if key in _RECENT_CHECKIN_CACHE:
        if now - _RECENT_CHECKIN_CACHE[key] < _RECENT_CHECKIN_TTL_SEC:
            return True
        else:
            del _RECENT_CHECKIN_CACHE[key]
    return False


def _cache_recent_mark(student_id: str, subject_id: str, dt: date) -> None:
    """Record that we just marked this student/subject/date."""
    key = (student_id, subject_id, dt.isoformat())
    _RECENT_CHECKIN_CACHE[key] = time.monotonic()
    # Prune old entries periodically (keep dict small)
    if len(_RECENT_CHECKIN_CACHE) > 1000:
        now = time.monotonic()
        cutoff = now - _RECENT_CHECKIN_TTL_SEC
        to_del = [k for k, v in _RECENT_CHECKIN_CACHE.items() if v < cutoff]
        for k in to_del:
            del _RECENT_CHECKIN_CACHE[k]


class AttendanceService:
    """Service for attendance operations."""

    @staticmethod
    def _get_client_info(request: Request | None) -> tuple[str | None, str | None]:
        """Extract IP and device info from request."""
        ip_address = None
        device_info = None
        if request:
            ip_address = request.client.host if request.client else None
            device_info = request.headers.get("user-agent", "")
        return ip_address, device_info

    @staticmethod
    async def mark_check_in(
        student_id: str,
        subject_id: str,
        confidence_score: float,
        user_id: str,
        request: Request | None = None,
    ) -> dict[str, Any]:
        """Mark check-in for a student. Returns structured response for success or already_marked."""
        ip_address, device_info = AttendanceService._get_client_info(request)
        today = date.today()

        student = await StudentRepository.get_by_id(student_id)
        student_name = (student or {}).get("name", "Unknown")

        # 0. In-memory debounce: skip if same student/subject/date was just marked (camera loop)
        if _was_recently_marked(student_id, subject_id, today):
            existing = await AttendanceRepository.get_by_student_date_subject(
                student_id, subject_id, today
            )
            return {
                "status": "already_marked",
                "student_name": student_name,
                "message": "Attendance already marked today",
                "record": existing or {},
            }

        # 1. Check if record already exists (avoids unnecessary insert)
        existing = await AttendanceRepository.get_by_student_date_subject(
            student_id, subject_id, today
        )
        if existing:
            await LogRepository.create(
                user_id=user_id,
                action="attendance_duplicate_attempt",
                ip_address=ip_address,
                device_info=device_info,
                details={
                    "student_id": student_id,
                    "subject_id": subject_id,
                    "date": today.isoformat(),
                },
            )
            _cache_recent_mark(student_id, subject_id, today)
            return {
                "status": "already_marked",
                "student_name": student_name,
                "message": "Attendance already marked today",
                "record": existing,
            }

        # 2. Insert new record (race condition protected by DB unique constraint)
        try:
            attendance = AttendanceCreate(
                student_id=student_id,
                subject_id=subject_id,
                date=today,
                status=AttendanceStatus.PRESENT,
                confidence_score=confidence_score,
                check_in=datetime.now().time(),
                ip_address=ip_address,
                device_info=device_info,
            )
            record = await AttendanceRepository.create(attendance)

            await LogRepository.create(
                user_id=user_id,
                action="attendance_check_in",
                ip_address=ip_address,
                device_info=device_info,
                details={"student_id": student_id, "subject_id": subject_id},
            )
            _cache_recent_mark(student_id, subject_id, today)
            return {
                "status": "success",
                "student_name": student_name,
                "message": "Attendance marked successfully",
                "confidence": confidence_score,
                "record": record,
            }
        except Exception as e:
            if _is_duplicate_error(e):
                await LogRepository.create(
                    user_id=user_id,
                    action="attendance_duplicate_attempt",
                    ip_address=ip_address,
                    device_info=device_info,
                    details={
                        "student_id": student_id,
                        "subject_id": subject_id,
                        "date": today.isoformat(),
                        "reason": "race_condition_caught",
                    },
                )
                _cache_recent_mark(student_id, subject_id, today)
                existing = await AttendanceRepository.get_by_student_date_subject(
                    student_id, subject_id, today
                )
                return {
                    "status": "already_marked",
                    "student_name": student_name,
                    "message": "Attendance already marked today",
                    "record": existing or {},
                }
            raise

    @staticmethod
    async def mark_check_out(
        student_id: str,
        subject_id: str,
        user_id: str,
        request: Request | None = None,
    ) -> dict[str, Any]:
        """Mark check-out for a student."""
        today = date.today()
        existing = await AttendanceRepository.get_by_student_date_subject(
            student_id, subject_id, today
        )
        if not existing:
            raise NotFoundError("No check-in record found for today")
        if existing.get("check_out"):
            raise DuplicateError("Check-out already recorded")

        updated = await AttendanceRepository.update_check_out(
            existing["id"], datetime.now().time().isoformat()
        )

        ip_address, device_info = AttendanceService._get_client_info(request)
        await LogRepository.create(
            user_id=user_id,
            action="attendance_check_out",
            ip_address=ip_address,
            device_info=device_info,
            details={"student_id": student_id, "subject_id": subject_id},
        )
        return updated

    @staticmethod
    async def get_student_attendance(
        student_id: str,
        subject_id: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """Get attendance records for a student."""
        return await AttendanceRepository.get_by_student(
            student_id, subject_id, start_date, end_date
        )

    @staticmethod
    async def get_attendance_summary(student_id: str, subject_id: str) -> dict[str, Any]:
        """Get attendance percentage summary."""
        return await AttendanceRepository.get_summary(student_id, subject_id)

    @staticmethod
    async def get_daily_report(subject_id: str, report_date: date) -> list[dict[str, Any]]:
        """Get daily attendance report for a subject."""
        return await AttendanceRepository.get_daily_report(subject_id, report_date)

    @staticmethod
    async def get_dashboard_stats(report_date: date | None = None) -> dict[str, Any]:
        """Get dashboard stats: today's attendance, total students, attendance rate, active sessions."""
        today = report_date or date.today()
        att_stats = await AttendanceRepository.get_dashboard_stats(today)
        total_students = await StudentRepository.get_count()

        # Attendance rate: present slots this month / (working_days * total_students)
        working_days = att_stats["working_days_this_month"]
        present_count = att_stats["present_this_month"]
        total_possible = working_days * total_students if total_students else 0
        attendance_rate = round((present_count / total_possible * 100), 1) if total_possible > 0 else 0

        return {
            "today_count": att_stats["today_count"],
            "total_students": total_students,
            "attendance_rate": attendance_rate,
            "active_sessions": att_stats["active_sessions"],
        }

    @staticmethod
    async def get_attendance_analytics(
        start_date: date | None = None,
        end_date: date | None = None,
        subject_id: str | None = None,
    ) -> dict[str, Any]:
        """Get attendance chart data for a date range (daily breakdown). Optional subject filter."""
        today = date.today()
        if not start_date:
            start_date = today - timedelta(days=6)
        if not end_date:
            end_date = today
        if start_date > end_date:
            start_date, end_date = end_date, start_date
        records = await AttendanceRepository.get_analytics_by_date_range(
            start_date, end_date, subject_id
        )
        total_students = 0
        if subject_id and records:
            total_students = len({r["student_id"] for r in records})
        if total_students == 0:
            total_students = await StudentRepository.get_count()
        by_date: dict[str, set[str]] = {}
        current = start_date
        while current <= end_date:
            by_date[current.isoformat()] = set()
            current += timedelta(days=1)
        for r in records:
            if r.get("status") == AttendanceStatus.PRESENT.value and r.get("date"):
                dt = r["date"][:10] if isinstance(r["date"], str) else str(r["date"])[:10]
                if dt in by_date:
                    by_date[dt].add(r["student_id"])
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        data = []
        current = start_date
        while current <= end_date:
            present = len(by_date.get(current.isoformat(), set()))
            absent = max(0, total_students - present)
            data.append({
                "name": day_names[current.weekday()],
                "label": current.strftime("%b %d"),
                "present": present,
                "absent": absent,
            })
            current += timedelta(days=1)
        return {"data": data, "total_students": total_students}

    @staticmethod
    async def get_attendance_report(
        start_date: date | None = None,
        end_date: date | None = None,
        subject_id: str | None = None,
        expected_classes: int | None = None,
        threshold: float | None = None,
    ) -> list[dict]:
        """Get per-student attendance report for export. If subject_id: filter by subject. Else: all subjects."""
        today = date.today()
        if not start_date:
            start_date = today - timedelta(days=6)
        if not end_date:
            end_date = today
        if start_date > end_date:
            start_date, end_date = end_date, start_date
        return await AttendanceRepository.get_attendance_report_by_date_range(
            start_date, end_date, subject_id, expected_classes, threshold
        )

    @staticmethod
    async def get_low_attendance_preview(year: int | None = None, month: int | None = None) -> dict:
        """Get list of students with attendance below 60% for the given month. No SMS sent."""
        today = date.today()
        check_year = year or today.year
        check_month = month or today.month

        students = await StudentRepository.get_all()
        low_attendance_list = []

        for student in students:
            parent_phone = (student.get("parent_phone") or "").strip()
            summary = await AttendanceRepository.get_monthly_summary(
                student["id"], check_year, check_month
            )
            if summary["working_days"] > 0 and summary["percentage"] < 60:
                low_attendance_list.append({
                    "student_id": student["id"],
                    "student_name": student["name"],
                    "parent_phone": parent_phone[:6] + "****" if len(parent_phone) >= 10 else "—",
                    "percentage": summary["percentage"],
                    "has_phone": bool(parent_phone and len(parent_phone) >= 10),
                })

        return {
            "total_students": len(students),
            "month": check_month,
            "year": check_year,
            "low_attendance_count": len(low_attendance_list),
            "low_attendance": low_attendance_list,
        }

    @staticmethod
    async def send_low_attendance_alerts(year: int | None = None, month: int | None = None) -> dict:
        """Send SMS to parents when student attendance is below 60% for the given month.
        Runs for every month - use year/month to check a specific month.
        Default: current month.
        """
        today = date.today()
        check_year = year or today.year
        check_month = month or today.month
        settings = get_settings()
        school_name = settings.SCHOOL_NAME

        sms_configured = SMSService._is_configured()

        students = await StudentRepository.get_all()
        sent = 0
        low_attendance_list = []

        for student in students:
            parent_phone = (student.get("parent_phone") or "").strip()
            summary = await AttendanceRepository.get_monthly_summary(
                student["id"], check_year, check_month
            )
            if summary["working_days"] > 0 and summary["percentage"] < 60:
                low_attendance_list.append({
                    "student_name": student["name"],
                    "percentage": summary["percentage"],
                    "has_phone": bool(parent_phone and len(parent_phone) >= 10),
                })
                if parent_phone and len(parent_phone) >= 10:
                    ok = await SMSService.send_low_attendance_alert(
                        parent_phone=parent_phone,
                        student_name=student["name"],
                        school_name=school_name,
                    )
                    if ok:
                        sent += 1

        result = {
            "sent": sent,
            "total_students": len(students),
            "month": check_month,
            "year": check_year,
            "low_attendance_count": len(low_attendance_list),
            "low_attendance": [
                {"student_name": x["student_name"], "percentage": x["percentage"]}
                for x in low_attendance_list
            ],
        }
        if not sms_configured and low_attendance_list:
            result["sms_error"] = "FAST2SMS_API_KEY is not configured. Add it to your environment variables."
        elif low_attendance_list and sent == 0:
            result["sms_error"] = "SMS failed to send. Check FAST2SMS_API_KEY and account balance (min 100 INR required)."
        return result

    @staticmethod
    async def get_low_attendance_preview(year: int | None = None, month: int | None = None) -> dict:
        """Get preview of students with low attendance (<60%) for the given month.
        Returns list of students with low attendance, count, and whether they have phone for SMS.
        """
        today = date.today()
        check_year = year or today.year
        check_month = month or today.month

        students = await StudentRepository.get_all()
        low_attendance_list = []

        for student in students:
            parent_phone = (student.get("parent_phone") or "").strip()
            summary = await AttendanceRepository.get_monthly_summary(
                student["id"], check_year, check_month
            )
            if summary["working_days"] > 0 and summary["percentage"] < 60:
                low_attendance_list.append({
                    "student_id": student["id"],
                    "student_name": student["name"],
                    "percentage": summary["percentage"],
                    "has_phone": bool(parent_phone and len(parent_phone) >= 10),
                })

        return {
            "low_attendance": low_attendance_list,
            "low_attendance_count": len(low_attendance_list),
            "month": check_month,
            "year": check_year,
        }

    @staticmethod
    async def send_custom_attendance_message(
        year: int | None = None,
        month: int | None = None,
        threshold: float = 60.0,
        message: str = "",
    ) -> dict:
        """Send custom SMS message to students with attendance below the given threshold for the month."""
        today = date.today()
        check_year = year or today.year
        check_month = month or today.month
        settings = get_settings()
        school_name = settings.SCHOOL_NAME

        sms_configured = SMSService._is_configured()

        students = await StudentRepository.get_all()
        sent = 0
        target_students = []

        for student in students:
            parent_phone = (student.get("parent_phone") or "").strip()
            summary = await AttendanceRepository.get_monthly_summary(
                student["id"], check_year, check_month
            )
            if summary["working_days"] > 0 and summary["percentage"] < threshold:
                target_students.append({
                    "student_name": student["name"],
                    "percentage": summary["percentage"],
                    "has_phone": bool(parent_phone and len(parent_phone) >= 10),
                })
                if parent_phone and len(parent_phone) >= 10:
                    ok = await SMSService.send_custom_message(
                        parent_phone=parent_phone,
                        message=message,
                        student_name=student["name"],
                        school_name=school_name,
                    )
                    if ok:
                        sent += 1

        result = {
            "sent": sent,
            "target_count": len(target_students),
            "month": check_month,
            "year": check_year,
            "threshold": threshold,
            "message": message,
            "target_students": [
                {"student_name": x["student_name"], "percentage": x["percentage"]}
                for x in target_students
            ],
        }
        if not sms_configured and target_students:
            result["sms_error"] = "FAST2SMS_API_KEY is not configured."
        elif target_students and sent == 0:
            result["sms_error"] = "SMS failed to send."
        return result

    @staticmethod
    async def send_low_attendance_alerts_bulk(
        student_ids: list[str],
        year: int | None = None,
        month: int | None = None,
    ) -> dict:
        """Send SMS to selected students with low attendance for the given month."""
        today = date.today()
        check_year = year or today.year
        check_month = month or today.month
        settings = get_settings()
        school_name = settings.SCHOOL_NAME

        sms_configured = SMSService._is_configured()

        sent = 0
        low_attendance_list = []

        for student_id in student_ids:
            student = await StudentRepository.get_by_id(student_id)
            if not student:
                continue
            parent_phone = (student.get("parent_phone") or "").strip()
            summary = await AttendanceRepository.get_monthly_summary(
                student_id, check_year, check_month
            )
            if summary["working_days"] > 0 and summary["percentage"] < 60:
                low_attendance_list.append({
                    "student_name": student["name"],
                    "percentage": summary["percentage"],
                    "has_phone": bool(parent_phone and len(parent_phone) >= 10),
                })
                if parent_phone and len(parent_phone) >= 10:
                    ok = await SMSService.send_low_attendance_alert(
                        parent_phone=parent_phone,
                        student_name=student["name"],
                        school_name=school_name,
                    )
                    if ok:
                        sent += 1

        result = {
            "sent": sent,
            "total_selected": len(student_ids),
            "month": check_month,
            "year": check_year,
            "low_attendance_count": len(low_attendance_list),
            "low_attendance": [
                {"student_name": x["student_name"], "percentage": x["percentage"]}
                for x in low_attendance_list
            ],
        }
        if not sms_configured and low_attendance_list:
            result["sms_error"] = "FAST2SMS_API_KEY is not configured."
        elif low_attendance_list and sent == 0:
            result["sms_error"] = "SMS failed to send."
        return result

    @staticmethod
    async def get_student_detailed_report(
        student_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        """Get detailed attendance report for a student, including per-subject breakdown."""
        today = date.today()
        if not start_date:
            start_date = today - timedelta(days=30)  # Last 30 days default
        if not end_date:
            end_date = today
        if start_date > end_date:
            start_date, end_date = end_date, start_date

        records = await AttendanceRepository.get_by_student(student_id, start_date=start_date, end_date=end_date)
        student = await StudentRepository.get_by_id(student_id)
        subjects = await SubjectRepository.get_all()

        subject_map = {s["id"]: s["name"] for s in subjects}
        by_subject = {}
        for record in records:
            subj_id = record["subject_id"]
            subj_name = subject_map.get(subj_id, "Unknown")
            if subj_name not in by_subject:
                by_subject[subj_name] = {"total": 0, "present": 0, "records": []}
            by_subject[subj_name]["total"] += 1
            if record["status"] == AttendanceStatus.PRESENT.value:
                by_subject[subj_name]["present"] += 1
            by_subject[subj_name]["records"].append(record)

        overall = {"total": sum(s["total"] for s in by_subject.values()), "present": sum(s["present"] for s in by_subject.values())}
        overall["percentage"] = int(round((overall["present"] / overall["total"] * 100), 0)) if overall["total"] > 0 else 0

        return {
            "student": student,
            "period": {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
            "overall": overall,
            "by_subject": by_subject,
            "records": records,
        }
