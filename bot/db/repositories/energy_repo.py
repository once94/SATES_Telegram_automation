from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models.energy_meter import EnergyMeter
from bot.db.models.energy_reading import EnergyReading


async def get_all_meters(session: AsyncSession, active_only: bool = True) -> list[EnergyMeter]:
    stmt = select(EnergyMeter)
    if active_only:
        stmt = stmt.where(EnergyMeter.is_active == True)
    result = await session.execute(stmt.order_by(EnergyMeter.name))
    return list(result.scalars().all())


async def get_meter_by_id(session: AsyncSession, meter_id: int) -> EnergyMeter | None:
    result = await session.execute(
        select(EnergyMeter).where(EnergyMeter.id == meter_id)
    )
    return result.scalar_one_or_none()


async def get_meter_by_name(session: AsyncSession, name: str) -> EnergyMeter | None:
    result = await session.execute(
        select(EnergyMeter).where(EnergyMeter.name == name)
    )
    return result.scalar_one_or_none()


async def create_meter(
    session: AsyncSession,
    name: str,
    meter_type: str,
    unit: str,
    location: str | None = None,
    description: str | None = None,
) -> EnergyMeter:
    meter = EnergyMeter(
        name=name,
        meter_type=meter_type,
        unit=unit,
        location=location,
        description=description,
    )
    session.add(meter)
    await session.flush()
    return meter


async def create_reading(
    session: AsyncSession,
    meter_id: int,
    reading_value: float,
    reading_date: date,
    recorded_by_id: int,
    difference: float | None = None,
    photo_file_id: str | None = None,
    ai_raw_response: str | None = None,
    confidence: float | None = None,
    notes: str | None = None,
) -> EnergyReading:
    reading = EnergyReading(
        meter_id=meter_id,
        reading_value=reading_value,
        reading_date=reading_date,
        recorded_by_id=recorded_by_id,
        difference=difference,
        photo_file_id=photo_file_id,
        ai_raw_response=ai_raw_response,
        confidence=confidence,
        notes=notes,
    )
    session.add(reading)
    await session.flush()
    return reading


async def get_last_reading(
    session: AsyncSession, meter_id: int
) -> EnergyReading | None:
    result = await session.execute(
        select(EnergyReading)
        .where(EnergyReading.meter_id == meter_id)
        .order_by(EnergyReading.reading_date.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_readings_for_meter(
    session: AsyncSession, meter_id: int, limit: int = 10
) -> list[EnergyReading]:
    result = await session.execute(
        select(EnergyReading)
        .where(EnergyReading.meter_id == meter_id)
        .order_by(EnergyReading.reading_date.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_reading_by_id(
    session: AsyncSession, reading_id: int
) -> EnergyReading | None:
    result = await session.execute(
        select(EnergyReading).where(EnergyReading.id == reading_id)
    )
    return result.scalar_one_or_none()


async def update_reading_value(
    session: AsyncSession, reading_id: int, new_value: float
) -> EnergyReading | None:
    reading = await get_reading_by_id(session, reading_id)
    if reading:
        reading.reading_value = new_value
        # Recalculate difference
        prev = await session.execute(
            select(EnergyReading)
            .where(
                EnergyReading.meter_id == reading.meter_id,
                EnergyReading.reading_date < reading.reading_date,
            )
            .order_by(EnergyReading.reading_date.desc())
            .limit(1)
        )
        prev_reading = prev.scalar_one_or_none()
        reading.difference = (
            new_value - prev_reading.reading_value if prev_reading else None
        )
    return reading
