import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models.audit_entry import AuditEntry
from bot.db.models.audit_report import AuditReport


async def create_audit_entry(
    session: AsyncSession,
    author_id: int,
    week_year: str,
    message_text: str | None = None,
    photo_file_ids: list[str] | None = None,
    message_id: int | None = None,
) -> AuditEntry:
    entry = AuditEntry(
        author_id=author_id,
        message_text=message_text,
        photo_file_ids=json.dumps(photo_file_ids) if photo_file_ids else None,
        message_id=message_id,
        week_year=week_year,
    )
    session.add(entry)
    await session.flush()
    return entry


async def get_entries_for_week(
    session: AsyncSession, week_year: str
) -> list[AuditEntry]:
    result = await session.execute(
        select(AuditEntry)
        .where(AuditEntry.week_year == week_year)
        .order_by(AuditEntry.created_at.asc())
    )
    return list(result.scalars().all())


async def create_audit_report(
    session: AsyncSession,
    week_year: str,
    report_text: str,
    summary: str | None,
    entries_count: int,
) -> AuditReport:
    report = AuditReport(
        week_year=week_year,
        report_text=report_text,
        summary=summary,
        entries_count=entries_count,
    )
    session.add(report)
    await session.flush()
    return report


async def mark_report_sent(
    session: AsyncSession,
    report_id: int,
    sent_to_group: bool,
    sent_to_user_ids: list[int],
) -> None:
    result = await session.execute(
        select(AuditReport).where(AuditReport.id == report_id)
    )
    report = result.scalar_one_or_none()
    if report:
        report.sent_at = datetime.utcnow()
        report.sent_to_group = sent_to_group
        report.sent_to_users = json.dumps(sent_to_user_ids)


async def mark_entries_included(
    session: AsyncSession, week_year: str, report_id: int
) -> None:
    entries = await get_entries_for_week(session, week_year)
    for entry in entries:
        entry.included_in_report_id = report_id


async def get_report_by_week(
    session: AsyncSession, week_year: str
) -> AuditReport | None:
    result = await session.execute(
        select(AuditReport).where(AuditReport.week_year == week_year)
    )
    return result.scalar_one_or_none()


async def get_recent_reports(
    session: AsyncSession, limit: int = 10
) -> list[AuditReport]:
    result = await session.execute(
        select(AuditReport).order_by(AuditReport.generated_at.desc()).limit(limit)
    )
    return list(result.scalars().all())
