from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from bot.db.base import Base


class AuditReport(Base):
    __tablename__ = "audit_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    week_year: Mapped[str] = mapped_column(String(10), unique=True)  # "2026-W15"
    report_text: Mapped[str] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    entries_count: Mapped[int] = mapped_column(Integer, default=0)
    generated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sent_to_group: Mapped[bool] = mapped_column(Boolean, default=False)
    sent_to_users: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list
