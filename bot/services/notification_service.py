import logging

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.db.repositories.user_repo import get_audit_report_recipients

logger = logging.getLogger(__name__)


async def send_to_group_topic(
    bot: Bot, text: str, thread_id: int, parse_mode: str = "HTML"
) -> None:
    """Send a message to a specific topic in the group."""
    try:
        for i in range(0, len(text), 4000):
            await bot.send_message(
                chat_id=settings.GROUP_CHAT_ID,
                message_thread_id=thread_id,
                text=text[i : i + 4000],
                parse_mode=parse_mode,
            )
    except Exception as e:
        logger.error("Failed to send to group topic %s: %s", thread_id, e)


async def send_dm(bot: Bot, telegram_id: int, text: str, parse_mode: str = "HTML") -> bool:
    """Send a DM to a user. Returns True if successful."""
    try:
        await bot.send_message(
            chat_id=telegram_id,
            text=text,
            parse_mode=parse_mode,
        )
        return True
    except Exception as e:
        logger.warning("Failed to send DM to %s: %s", telegram_id, e)
        return False


async def send_audit_report_notifications(
    bot: Bot,
    session: AsyncSession,
    report_text: str,
    summary: str,
    week_year: str,
) -> list[int]:
    """Send audit report to group + DM to recipients. Returns list of notified telegram_ids."""
    # Send full report to group
    await send_to_group_topic(
        bot,
        f"<b>Tyzdenny audit report ({week_year})</b>\n\n{report_text}",
        settings.TOPIC_AUDITS,
    )

    # Send short summary via DM
    recipients = await get_audit_report_recipients(session)
    notified = []
    for user in recipients:
        ok = await send_dm(
            bot,
            user.telegram_id,
            f"<b>Tyzdenny audit report ({week_year})</b>\n\n{summary}",
        )
        if ok:
            notified.append(user.telegram_id)

    return notified
