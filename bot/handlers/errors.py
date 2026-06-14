import logging
import traceback

from aiogram import Bot, Router
from aiogram.types import ErrorEvent

from bot.config import settings
from bot.services.notification_service import send_dm

logger = logging.getLogger(__name__)
router = Router(name="errors")


@router.errors()
async def global_error_handler(event: ErrorEvent, bot: Bot) -> bool:
    """Catch unhandled exceptions, log them, and DM the first admin."""
    exc = event.exception
    update = event.update

    # Identify the originating user, if any
    user_info = ""
    src = None
    if update.message and update.message.from_user:
        src = update.message.from_user
    elif update.callback_query and update.callback_query.from_user:
        src = update.callback_query.from_user
    if src:
        user_info = f"Od: {src.full_name} (@{src.username}, {src.id})\n"

    logger.error("Unhandled exception: %s", exc, exc_info=exc)

    if not settings.admin_ids:
        return True

    admin_id = settings.admin_ids[0]

    if settings.DEBUG:
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        tb = tb[-1500:]  # fit within Telegram message limit
        text = (
            f"<b>Bot chyba</b>\n{user_info}"
            f"<b>Typ:</b> <code>{type(exc).__name__}</code>\n"
            f"<b>Chyba:</b> {exc}\n\n"
            f"<pre>{tb}</pre>"
        )
    else:
        text = (
            f"<b>Bot chyba</b>\n{user_info}"
            f"<code>{type(exc).__name__}: {exc}</code>"
        )

    await send_dm(bot, admin_id, text)
    return True
