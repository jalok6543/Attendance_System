"""Scheduler for automatic low attendance SMS alerts at end of every month."""

from datetime import date

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.services.attendance_service import AttendanceService


async def _run_monthly_alerts():
    """Run low attendance alerts for the previous month (called on 1st of each month)."""
    today = date.today()
    if today.month == 1:
        prev_year, prev_month = today.year - 1, 12
    else:
        prev_year, prev_month = today.year, today.month - 1

    try:
        result = await AttendanceService.send_low_attendance_alerts(
            year=prev_year, month=prev_month
        )
        sent = result.get("sent", 0)
        low = result.get("low_attendance_count", 0)
        if sent > 0 or low > 0:
            print(f"[Scheduler] Low attendance alerts: sent {sent} SMS for {low} students ({prev_year}-{prev_month})")
    except Exception as e:
        print(f"[Scheduler] Low attendance alerts failed: {e}")


def start_scheduler(enabled: bool = True) -> AsyncIOScheduler | None:
    """Start the scheduler. Runs on 1st of every month at 9:00 AM for previous month."""
    if not enabled:
        return None

    scheduler = AsyncIOScheduler()
    # Run on 1st of every month at 9:00 AM - sends alerts for previous month
    scheduler.add_job(
        _run_monthly_alerts,
        CronTrigger(day=1, hour=9, minute=0),
        id="low_attendance_alerts",
        replace_existing=True,
    )
    scheduler.start()
    return scheduler
