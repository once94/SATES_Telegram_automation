import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.repositories import audit_repo
from bot.db.repositories.user_repo import get_audit_report_recipients
from bot.services.ai_vision import ai_vision_service
from bot.utils.formatting import format_date

logger = logging.getLogger(__name__)


async def generate_weekly_report(
    session: AsyncSession,
    week_year: str,
    bot=None,
) -> dict:
    """Generate and store weekly audit report."""
    entries = await audit_repo.get_entries_for_week(session, week_year)
    if not entries:
        return {"status": "no_entries"}

    # Prepare entries for AI
    entry_dicts = []
    photos: list[tuple[str, bytes]] = []

    for entry in entries:
        entry_dicts.append({
            "id": entry.id,
            "author": entry.author.full_name if entry.author else "Neznamy",
            "date": format_date(entry.created_at),
            "text": entry.message_text or "(iba fotka)",
        })

        # Download photos if bot is available
        if bot and entry.photo_file_ids:
            try:
                file_ids = json.loads(entry.photo_file_ids)
                for file_id in file_ids:
                    file = await bot.get_file(file_id)
                    data = await bot.download_file(file.file_path)
                    photos.append((entry.message_text or "", data.read()))
            except Exception as e:
                logger.error("Failed to download audit photo: %s", e)

    # Generate report via AI
    result = await ai_vision_service.generate_weekly_report(entry_dicts, photos)

    # Store report
    report = await audit_repo.create_audit_report(
        session,
        week_year=week_year,
        report_text=result.report_text,
        summary=result.summary,
        entries_count=len(entries),
    )

    # Mark entries as included
    await audit_repo.mark_entries_included(session, week_year, report.id)

    return {"status": "success", "report": report}
