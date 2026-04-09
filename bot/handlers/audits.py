import json
import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.db.models.user import User
from bot.db.repositories import audit_repo
from bot.filters.topic_filter import ForumTopicFilter
from bot.utils.formatting import get_week_year, format_date

logger = logging.getLogger(__name__)
router = Router(name="audits")


# --- Passive photo/text collector (only in audit topic) ---

@router.message(
    F.photo,
    ForumTopicFilter(thread_id=settings.TOPIC_AUDITS),
)
async def collect_audit_photo(message: Message, session: AsyncSession, db_user: User):
    photo_file_ids = [p.file_id for p in message.photo[-1:]]  # largest size
    caption = message.caption

    entry = await audit_repo.create_audit_entry(
        session,
        author_id=db_user.id,
        week_year=get_week_year(),
        message_text=caption,
        photo_file_ids=photo_file_ids,
        message_id=message.message_id,
    )
    await message.reply(f"Zaznam #{entry.id} ulozeny pre tyzdenny report.")


@router.message(
    F.text,
    ForumTopicFilter(thread_id=settings.TOPIC_AUDITS),
    ~F.text.startswith("/"),
)
async def collect_audit_text(message: Message, session: AsyncSession, db_user: User):
    entry = await audit_repo.create_audit_entry(
        session,
        author_id=db_user.id,
        week_year=get_week_year(),
        message_text=message.text,
        message_id=message.message_id,
    )
    await message.reply(f"Zaznam #{entry.id} ulozeny pre tyzdenny report.")


# --- Commands ---

@router.message(Command("audit_zoznam"))
async def cmd_audit_list(message: Message, session: AsyncSession):
    reports = await audit_repo.get_recent_reports(session, limit=10)
    if not reports:
        await message.answer("Zatial neboli vygenerovane ziadne tyzdenne reporty.")
        return

    lines = ["<b>Posledne tyzdenne reporty:</b>\n"]
    for r in reports:
        status = "odoslany" if r.sent_to_group else "novy"
        lines.append(
            f" {r.week_year} | {r.entries_count} zaznamov | {status} | {format_date(r.generated_at)}"
        )
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("audit_report"))
async def cmd_audit_report(message: Message, session: AsyncSession):
    args = message.text.split(maxsplit=1)
    week = args[1].strip() if len(args) > 1 else get_week_year()

    report = await audit_repo.get_report_by_week(session, week)
    if not report:
        entries = await audit_repo.get_entries_for_week(session, week)
        if entries:
            await message.answer(
                f"Report pre {week} este nebol vygenerovany.\n"
                f"Pocet zaznamov: {len(entries)}.\n"
                "Report sa generuje automaticky v pondelok o 8:00."
            )
        else:
            await message.answer(f"Pre tyzden {week} nie su ziadne zaznamy ani report.")
        return

    # Split long reports into chunks (Telegram limit 4096 chars)
    text = f"<b>Tyzdenny report {report.week_year}</b>\n\n{report.report_text}"
    for i in range(0, len(text), 4000):
        await message.answer(text[i : i + 4000], parse_mode="HTML")


@router.message(Command("audit_notifikacie"))
async def cmd_audit_notifications(message: Message, session: AsyncSession, db_user: User):
    db_user.receive_audit_reports = not db_user.receive_audit_reports
    status = "ZAPNUTE" if db_user.receive_audit_reports else "VYPNUTE"
    await message.answer(
        f"DM notifikacie pre tyzdenne audit reporty: <b>{status}</b>",
        parse_mode="HTML",
    )
