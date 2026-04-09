import logging
from datetime import datetime

from aiogram import Bot
from sqlalchemy.ext.asyncio import async_sessionmaker

from bot.config import settings

logger = logging.getLogger(__name__)


async def check_task_reminders(
    bot: Bot, session_factory: async_sessionmaker
) -> None:
    from bot.db.repositories.task_repo import get_tasks_needing_reminder

    async with session_factory() as session:
        tasks = await get_tasks_needing_reminder(session)
        for task in tasks:
            try:
                assigned = task.assigned_to
                mention = f"@{assigned.username}" if assigned.username else assigned.full_name

                text = (
                    f"Pripomienka ulohy #{task.id}\n"
                    f"Pridelena: {mention}\n"
                    f"Popis: {task.title}"
                )
                if task.due_date:
                    text += f"\nTermin: {task.due_date.strftime('%d.%m.%Y')}"

                if task.topic_thread_id:
                    await bot.send_message(
                        chat_id=settings.GROUP_CHAT_ID,
                        message_thread_id=task.topic_thread_id,
                        text=text,
                    )
                else:
                    await bot.send_message(
                        chat_id=settings.GROUP_CHAT_ID,
                        text=text,
                    )

                task.last_reminded_at = datetime.utcnow()
            except Exception as e:
                logger.error("Failed to send reminder for task %s: %s", task.id, e)

        await session.commit()
