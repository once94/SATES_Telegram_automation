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
    meters = await energy_repo.get_all_meters(session)

    meter = None
    if len(meters) == 1:
        meter = meters[0]
    elif len(meters) > 1:
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

    # Read the meter value (with dual_tariff flag)
    result = await ai_vision_service.read_meter(
        photo_bytes=photo_bytes,
        meter_type=meter.meter_type,
        dual_tariff=meter.dual_tariff,
    )

    if result.value is None or result.confidence < 0.5:
        return {"status": "low_confidence", "ai_result": result}

    # Calculate differences from previous reading
    last_reading = await energy_repo.get_last_reading(session, meter.id)
    difference = None
    difference_vt = None
    difference_nt = None
    if last_reading:
        difference = result.value - last_reading.reading_value
        if meter.dual_tariff and result.value_vt is not None and last_reading.reading_value_vt is not None:
            difference_vt = result.value_vt - last_reading.reading_value_vt
        if meter.dual_tariff and result.value_nt is not None and last_reading.reading_value_nt is not None:
            difference_nt = result.value_nt - last_reading.reading_value_nt

    # Store the reading
    reading = await energy_repo.create_reading(
        session,
        meter_id=meter.id,
        reading_value=result.value,
        reading_value_vt=result.value_vt,
        reading_value_nt=result.value_nt,
        reading_date=date.today(),
        recorded_by_id=recorded_by.id,
        difference=difference,
        difference_vt=difference_vt,
        difference_nt=difference_nt,
        photo_file_id=photo_file_id,
        ai_raw_response=result.raw_response,
        confidence=result.confidence,
    )

    return {"status": "success", "reading": reading, "meter": meter}
