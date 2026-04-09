from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.db.base import Base


class EnergyReading(Base):
    __tablename__ = "energy_readings"

    id: Mapped[int] = mapped_column(primary_key=True)
    meter_id: Mapped[int] = mapped_column(ForeignKey("energy_meters.id"))
    reading_value: Mapped[float] = mapped_column(Float)
    reading_date: Mapped[date] = mapped_column(Date)
    recorded_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    difference: Mapped[float | None] = mapped_column(Float, nullable=True)
    photo_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ai_raw_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    meter = relationship("EnergyMeter", lazy="joined")
    recorded_by = relationship("User", lazy="joined")
