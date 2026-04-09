from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import settings
from bot.db.base import session_factory
from bot.handlers import get_main_router
from bot.middlewares.db_session import DbSessionMiddleware
from bot.middlewares.user_registry import UserRegistryMiddleware


def create_bot() -> Bot:
    return Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher()

    # Register middlewares
    dp.message.middleware(DbSessionMiddleware(session_factory))
    dp.message.middleware(UserRegistryMiddleware())
    dp.callback_query.middleware(DbSessionMiddleware(session_factory))
    dp.callback_query.middleware(UserRegistryMiddleware())

    # Include routers
    dp.include_router(get_main_router())

    return dp
