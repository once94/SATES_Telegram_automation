import logging

from aiogram import Bot
from sqlalchemy.ext.asyncio import async_sessionmaker

from bot.db.repositories import audit_repo
from bot.services.audit_service import generate_weekly_report
from bot.services.notification_service import send_audit_report_notifications
from bot.utils.formatting import get_previous_week_year

logger = logging.getLogger(__name__)


async def generate_weekly_audit(
    bot: Bot, session_factory: async_sessionmaker
) -> None:
    """Scheduled job: generate and send weekly audit report (Monday 8:00)."""
    week_year = get_previous_week_year()  # Report for the previous week
    logger.info("Generating weekly audit report for %s", week_year)

    async with session_factory() as session:
        # Check if already generated
        existing = await audit_repo.get_report_by_week(session, week_year)
        if existing and existing.sent_to_group:
            logger.info("Report for %s already sent, skipping", week_year)
            return

        result = await generate_weekly_report(session, week_year, bot=bot)

        if result["status"] == "no_entries":
            logger.info("No audit entries for %s, skipping report", week_year)
            return

        if result["status"] == "success":
            report = result["report"]
            notified = await send_audit_report_notifications(
                bot, session, report.report_text, report.summary or "", week_year
            )

            await audit_repo.mark_report_sent(
                session, report.id, sent_to_group=True, sent_to_user_ids=notified
            )
            await session.commit()
            logger.info(
                "Weekly audit report %s sent. Notified %d users.",
                week_year,
                len(notified),
            )
