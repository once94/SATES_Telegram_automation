from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models.user import User


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None,
    full_name: str,
) -> User:
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            telegram_id=telegram_id,
            username=username,
            full_name=full_name,
        )
        session.add(user)
        await session.flush()
    else:
        user.username = username
        user.full_name = full_name
    return user


async def get_user_by_telegram_id(
    session: AsyncSession, telegram_id: int
) -> User | None:
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


async def get_user_by_username(
    session: AsyncSession, username: str
) -> User | None:
    result = await session.execute(
        select(User).where(User.username == username)
    )
    return result.scalar_one_or_none()


async def get_audit_report_recipients(session: AsyncSession) -> list[User]:
    result = await session.execute(
        select(User).where(User.receive_audit_reports == True, User.is_active == True)
    )
    return list(result.scalars().all())
