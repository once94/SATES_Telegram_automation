from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.repositories.user_repo import get_or_create_user


class UserRegistryMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = None
        if isinstance(event, Message) and event.from_user:
            user = event.from_user
        elif isinstance(event, CallbackQuery) and event.from_user:
            user = event.from_user

        if user and "session" in data:
            session: AsyncSession = data["session"]
            db_user = await get_or_create_user(
                session,
                telegram_id=user.id,
                username=user.username,
                full_name=user.full_name or user.first_name or "Unknown",
            )
            data["db_user"] = db_user

        return await handler(event, data)
