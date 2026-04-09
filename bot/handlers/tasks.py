import logging
import re
from datetime import datetime

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.db.models.user import User
from bot.db.repositories import task_repo
from bot.db.repositories.user_repo import get_user_by_username
from bot.keyboards.inline import TaskAction, task_keyboard
from bot.utils.formatting import format_date

logger = logging.getLogger(__name__)
router = Router(name="tasks")


@router.message(Command("uloha_nova"))
async def cmd_task_new(message: Message, session: AsyncSession, db_user: User):
    text = message.text or ""
    # Parse: /uloha_nova @username Task description termin:2026-04-15
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "Pouzitie: /uloha_nova @user Popis ulohy [termin:RRRR-MM-DD]"
        )
        return

    rest = parts[1]

    # Extract username
    username_match = re.match(r"@(\w+)\s+", rest)
    if not username_match:
        await message.answer("Musis zadat @username uzivatela.")
        return

    username = username_match.group(1)
    rest = rest[username_match.end():]

    # Extract optional due date
    due_date = None
    due_match = re.search(r"termin:(\d{4}-\d{2}-\d{2})", rest)
    if due_match:
        try:
            due_date = datetime.strptime(due_match.group(1), "%Y-%m-%d")
        except ValueError:
            pass
        rest = rest[: due_match.start()].strip()

    title = rest.strip()
    if not title:
        await message.answer("Musis zadat popis ulohy.")
        return

    # Find target user
    target_user = await get_user_by_username(session, username)
    if not target_user:
        await message.answer(
            f"Uzivatel @{username} nebol najdeny. "
            "Musi najprv napisat do skupiny, aby bol zaregistrovany."
        )
        return

    task = await task_repo.create_task(
        session,
        title=title,
        assigned_to_id=target_user.id,
        assigned_by_id=db_user.id,
        topic_thread_id=message.message_thread_id,
        due_date=due_date,
    )

    due_text = f"\nTermin: {format_date(due_date)}" if due_date else ""
    await message.answer(
        f"Uloha #{task.id} vytvorena!\n"
        f"Pridelena: @{username}\n"
        f"Popis: {title}{due_text}",
        reply_markup=task_keyboard(task.id),
    )


@router.message(Command("uloha_zoznam"))
async def cmd_task_list(message: Message, session: AsyncSession, db_user: User):
    tasks = await task_repo.get_tasks_for_user(session, db_user.id)
    if not tasks:
        await message.answer("Nemas ziadne otvorene ulohy.")
        return

    lines = ["<b>Tvoje otvorene ulohy:</b>\n"]
    for t in tasks:
        due = f" | termin: {format_date(t.due_date)}" if t.due_date else ""
        lines.append(f"#{t.id} | {t.status} | {t.title}{due}")
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("uloha_hotovo"))
async def cmd_task_done(message: Message, session: AsyncSession):
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Pouzitie: /uloha_hotovo <id>")
        return

    try:
        task_id = int(parts[1])
    except ValueError:
        await message.answer("Nespravne ID ulohy.")
        return

    task = await task_repo.complete_task(session, task_id)
    if task:
        await message.answer(f"Uloha #{task_id} oznacena ako hotova!")
    else:
        await message.answer(f"Uloha #{task_id} nebola najdena.")


@router.message(Command("uloha_vsetky"))
async def cmd_task_all(message: Message, session: AsyncSession):
    tasks = await task_repo.get_all_open_tasks(session)
    if not tasks:
        await message.answer("Nie su ziadne otvorene ulohy.")
        return

    lines = ["<b>Vsetky otvorene ulohy:</b>\n"]
    for t in tasks:
        assigned = t.assigned_to
        name = f"@{assigned.username}" if assigned.username else assigned.full_name
        due = f" | termin: {format_date(t.due_date)}" if t.due_date else ""
        lines.append(f"#{t.id} | {name} | {t.title}{due}")
    await message.answer("\n".join(lines), parse_mode="HTML")


# --- Callback handlers ---

@router.callback_query(TaskAction.filter(F.action == "done"))
async def callback_task_done(
    callback: CallbackQuery, callback_data: TaskAction, session: AsyncSession
):
    task = await task_repo.complete_task(session, callback_data.task_id)
    if task:
        await callback.answer("Uloha oznacena ako hotova!")
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.reply(f"Uloha #{callback_data.task_id} - HOTOVO!")
    else:
        await callback.answer("Uloha nebola najdena.", show_alert=True)


@router.callback_query(TaskAction.filter(F.action == "cancel"))
async def callback_task_cancel(
    callback: CallbackQuery, callback_data: TaskAction, session: AsyncSession
):
    from sqlalchemy import select
    from bot.db.models.task import Task

    result = await session.execute(
        select(Task).where(Task.id == callback_data.task_id)
    )
    task = result.scalar_one_or_none()
    if task:
        task.status = "cancelled"
        await callback.answer("Uloha zrusena.")
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.reply(f"Uloha #{callback_data.task_id} - ZRUSENA")
    else:
        await callback.answer("Uloha nebola najdena.", show_alert=True)
