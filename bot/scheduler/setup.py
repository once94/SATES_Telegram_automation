import logging

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.db.base import session_factory

logger = logging.getLogger(__name__)


def create_scheduler(bot: Bot) -> AsyncIOScheduler:
    from bot.scheduler.task_reminders import check_task_reminders
    from bot.scheduler.weekly_audit_report import generate_weekly_audit

    scheduler = AsyncIOScheduler(timezone="Europe/Bratislava")

    # Task reminders - once per day at 8:30
    scheduler.add_job(
        check_task_reminders,
        "cron",
        hour=8,
        minute=30,
        kwargs={"bot": bot, "session_factory": session_factory},
        id="task_reminders",
        replace_existing=True,
    )

    # Weekly audit report - Monday at 8:00
    scheduler.add_job(
        generate_weekly_audit,
        "cron",
        day_of_week="mon",
        hour=8,
        minute=0,
        kwargs={"bot": bot, "session_factory": session_factory},
        id="weekly_audit",
        replace_existing=True,
    )

    return scheduler
