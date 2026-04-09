from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.db.base import Base


class AuditEntry(Base):
    __tablename__ = "audit_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    message_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_file_ids: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list
    message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    week_year: Mapped[str] = mapped_column(String(10))  # "2026-W15"
    included_in_report_id: Mapped[int | None] = mapped_column(
        ForeignKey("audit_reports.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    author = relationship("User", lazy="joined")
