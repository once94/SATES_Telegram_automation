import logging
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models.user import User
from bot.db.repositories import energy_repo
from bot.services.ai_vision import ai_vision_service

logger = logging.getLogger(__name__)


async def process_meter_photo(
    session: AsyncSession,
    photo_bytes: bytes,
    photo_file_id: str,
    recorded_by: User,
) -> dict:
    """Process a meter photo: identify meter, read value, store reading."""
    # Get all active meters
    meters = await energy_repo.get_all_meters(session)

    meter = None
    if len(meters) == 1:
        meter = meters[0]
    elif len(meters) > 1:
        # Try to identify which meter
        meter_dicts = [
            {"id": m.id, "name": m.name, "meter_type": m.meter_type, "location": m.location}
            for m in meters
        ]
        meter_id = await ai_vision_service.identify_meter(photo_bytes, meter_dicts)
        if meter_id:
            meter = await energy_repo.get_meter_by_id(session, meter_id)

    if not meter:
        if not meters:
            return {
                "status": "error",
                "error": "Nie su zaregistrovane ziadne merace. Pouzi /energia_novy_merac",
            }
        # Default to first meter if only one, otherwise ask user
        if len(meters) == 1:
            meter = meters[0]
        else:
            return {
                "status": "error",
                "error": (
                    "Nepodarilo sa identifikovat merac. "
                    "Skus pridat referencnu fotku alebo pouzi manualne zadanie."
                ),
            }

    # Read the meter value
    result = await ai_vision_service.read_meter(
        photo_bytes=photo_bytes,
        meter_type=meter.meter_type,
    )

    if result.value is None or result.confidence < 0.5:
        return {"status": "low_confidence", "ai_result": result}

    # Calculate difference from previous reading
    last_reading = await energy_repo.get_last_reading(session, meter.id)
    difference = None
    if last_reading:
        difference = result.value - last_reading.reading_value

    # Store the reading
    reading = await energy_repo.create_reading(
        session,
        meter_id=meter.id,
        reading_value=result.value,
        reading_date=date.today(),
        recorded_by_id=recorded_by.id,
        difference=difference,
        photo_file_id=photo_file_id,
        ai_raw_response=result.raw_response,
        confidence=result.confidence,
    )

    return {"status": "success", "reading": reading, "meter": meter}
