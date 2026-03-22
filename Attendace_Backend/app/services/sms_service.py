"""SMS service - Fast2SMS integration for attendance alerts."""

import logging
from typing import Optional

import httpx

from app.core.config import get_settings
from app.repositories.log_repository import LogRepository

logger = logging.getLogger(__name__)

FAST2SMS_URL = "https://www.fast2sms.com/dev/bulkV2"


def _normalize_phone_for_india(phone: str) -> Optional[str]:
    """Normalize phone to 10-digit Indian format for Fast2SMS. Returns None if invalid."""
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) >= 10:
        return digits[-10:]  # Use last 10 digits (handles +91 prefix)
    return digits if len(digits) == 10 else None


async def _send_sms_async(message: str, numbers: str) -> bool:
    """
    Send SMS via Fast2SMS API. Returns True on success, False on failure.
    Logs errors to logs table; does not raise.
    """
    settings = get_settings()
    api_key = getattr(settings, "FAST2SMS_API_KEY", "") or ""
    if not api_key or not numbers:
        return False

    payload = {
        "route": "q",
        "message": message,
        "language": "english",
        "numbers": numbers,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                FAST2SMS_URL,
                json=payload,
                headers={
                    "authorization": api_key,
                    "Content-Type": "application/json",
                },
            )
            data = response.json() if response.text else {}
            if response.status_code == 200 and data.get("return"):
                return True
            error_msg = data.get("message", response.text) or f"HTTP {response.status_code}"
            logger.warning("Fast2SMS failed: %s", error_msg)
            try:
                await LogRepository.create(
                    None,
                    "sms_send_failed",
                    details={"provider": "fast2sms", "error": str(error_msg), "numbers": numbers[:15]},
                )
            except Exception:
                logger.warning("Could not log SMS failure to logs table")
            return False
    except Exception as e:
        logger.exception("Fast2SMS request failed")
        try:
            await LogRepository.create(
                None,
                "sms_send_failed",
                details={"provider": "fast2sms", "error": str(e), "numbers": numbers[:15]},
            )
        except Exception:
            logger.warning("Could not log SMS failure to logs table")
        return False


class SMSService:
    """Service for sending SMS via Fast2SMS."""

    @staticmethod
    def _is_configured() -> bool:
        """Check if Fast2SMS API key is configured."""
        settings = get_settings()
        return bool(getattr(settings, "FAST2SMS_API_KEY", "") or "")

    @staticmethod
    async def send_absent_alert(parent_phone: str, student_name: str, subject_name: str) -> bool:
        """Send SMS when student is absent."""
        numbers = _normalize_phone_for_india(parent_phone)
        if not numbers or not SMSService._is_configured():
            return False

        message = (
            f"Attendance Alert: {student_name} was absent for {subject_name} today. "
            "Please contact the school for more details."
        )
        return await _send_sms_async(message, numbers)

    @staticmethod
    async def send_attendance_summary(
        parent_phone: str,
        student_name: str,
        percentage: float,
        subject_name: str,
    ) -> bool:
        """Send attendance summary to parent."""
        numbers = _normalize_phone_for_india(parent_phone)
        if not numbers or not SMSService._is_configured():
            return False

        status = "Good" if percentage >= 75 else "Low - Please ensure regular attendance"
        message = (
            f"Attendance Summary for {student_name}: {subject_name} - {percentage:.1f}% ({status})."
        )
        return await _send_sms_async(message, numbers)

    @staticmethod
    async def send_low_attendance_alert(
        parent_phone: str,
        student_name: str,
        school_name: str,
    ) -> bool:
        """Send SMS when student attendance is below 60%."""
        numbers = _normalize_phone_for_india(parent_phone)
        if not numbers or not SMSService._is_configured():
            return False

        settings = get_settings()
        school = school_name or settings.SCHOOL_NAME
        message = (
            f"Hello, this is a message from {school}. We would like to inform you that your child, "
            f"{student_name}, currently has attendance below the required minimum of 60%. Kindly ensure "
            "regular attendance to meet the school's attendance criteria. Thank you."
        )
        return await _send_sms_async(message, numbers)

    @staticmethod
    async def send_custom_message(
        parent_phone: str,
        message: str,
        student_name: str,
        school_name: str,
    ) -> bool:
        """Send custom SMS message to parent."""
        numbers = _normalize_phone_for_india(parent_phone)
        if not numbers or not SMSService._is_configured():
            return False

        settings = get_settings()
        school = school_name or settings.SCHOOL_NAME
        full_message = f"Hello, this is a message from {school} regarding {student_name}: {message}"
        return await _send_sms_async(full_message, numbers)
