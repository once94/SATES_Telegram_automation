from datetime import datetime

from sqlalchemy import Integer, String, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.db.base import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    topic_thread_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    assigned_to_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    assigned_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(50), default="pending")
    priority: Mapped[str] = mapped_column(String(50), default="normal")
    due_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reminder_interval_hours: Mapped[int] = mapped_column(Integer, default=24)
    last_reminded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    assigned_to = relationship("User", foreign_keys=[assigned_to_id], lazy="joined")
    assigned_by = relationship("User", foreign_keys=[assigned_by_id], lazy="joined")
