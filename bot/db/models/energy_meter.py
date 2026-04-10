from datetime import datetime

from sqlalchemy import Boolean, String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from bot.db.base import Base


class EnergyMeter(Base):
    __tablename__ = "energy_meters"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    meter_type: Mapped[str] = mapped_column(String(50))  # electricity, gas, water
    unit: Mapped[str] = mapped_column(String(20))  # kWh, m3, ...
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_photo_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dual_tariff: Mapped[bool] = mapped_column(Boolean, default=False)  # VT+NT elektromery
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
