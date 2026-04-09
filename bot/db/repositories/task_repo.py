from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models.task import Task


async def create_task(
    session: AsyncSession,
    title: str,
    assigned_to_id: int,
    assigned_by_id: int,
    topic_thread_id: int | None = None,
    due_date: datetime | None = None,
    priority: str = "normal",
) -> Task:
    task = Task(
        title=title,
        assigned_to_id=assigned_to_id,
        assigned_by_id=assigned_by_id,
        topic_thread_id=topic_thread_id,
        due_date=due_date,
        priority=priority,
    )
    session.add(task)
    await session.flush()
    return task


async def get_tasks_for_user(
    session: AsyncSession, user_id: int, include_done: bool = False
) -> list[Task]:
    stmt = select(Task).where(Task.assigned_to_id == user_id)
    if not include_done:
        stmt = stmt.where(Task.status.in_(["pending", "in_progress"]))
    stmt = stmt.order_by(Task.created_at.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_all_open_tasks(session: AsyncSession) -> list[Task]:
    result = await session.execute(
        select(Task)
        .where(Task.status.in_(["pending", "in_progress"]))
        .order_by(Task.created_at.desc())
    )
    return list(result.scalars().all())


async def complete_task(session: AsyncSession, task_id: int) -> Task | None:
    result = await session.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if task:
        task.status = "done"
        task.completed_at = datetime.utcnow()
    return task


async def get_tasks_needing_reminder(session: AsyncSession) -> list[Task]:
    now = datetime.utcnow()
    result = await session.execute(
        select(Task).where(
            Task.status.in_(["pending", "in_progress"]),
            (Task.last_reminded_at == None)  # noqa: E711
            | (
                Task.last_reminded_at
                < now - timedelta(hours=1)  # minimum 1h between reminders
            ),
        )
    )
    tasks = list(result.scalars().all())
    return [
        t
        for t in tasks
        if t.last_reminded_at is None
        or (now - t.last_reminded_at).total_seconds()
        >= t.reminder_interval_hours * 3600
    ]
