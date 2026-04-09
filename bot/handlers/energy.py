import logging
from datetime import date

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.db.models.user import User
from bot.db.repositories import energy_repo
from bot.filters.topic_filter import ForumTopicFilter
from bot.keyboards.inline import EnergyReadingAction, energy_reading_keyboard
from bot.services.ai_vision import ai_vision_service
from bot.services.energy_service import process_meter_photo
from bot.utils.formatting import format_number, format_date

logger = logging.getLogger(__name__)
router = Router(name="energy")


# --- Passive photo handler (only in energy topic) ---

@router.message(
    F.photo,
    ForumTopicFilter(thread_id=settings.TOPIC_ENERGY),
)
async def handle_energy_photo(message: Message, session: AsyncSession, db_user: User):
    await message.reply("Spracuvam fotku meraca...")

    photo = message.photo[-1]  # largest size
    file = await message.bot.get_file(photo.file_id)
    photo_bytes = await message.bot.download_file(file.file_path)

    result = await process_meter_photo(
        session=session,
        photo_bytes=photo_bytes.read(),
        photo_file_id=photo.file_id,
        recorded_by=db_user,
    )

    if result["status"] == "success":
        reading = result["reading"]
        meter = result["meter"]
        diff_text = ""
        if reading.difference is not None:
            diff_text = (
                f"\nPredchadzajuci: {format_number(reading.reading_value - reading.difference)} {meter.unit}"
                f"\nRozdiel: <b>{format_number(reading.difference)} {meter.unit}</b>"
            )

        await message.reply(
            f"<b>Merac:</b> {meter.name}\n"
            f"<b>Odcit:</b> {format_number(reading.reading_value)} {meter.unit}"
            f"{diff_text}\n"
            f"<b>Datum:</b> {format_date(reading.reading_date)}\n"
            f"<b>Istota AI:</b> {int((reading.confidence or 0) * 100)}%",
            parse_mode="HTML",
            reply_markup=energy_reading_keyboard(reading.id),
        )
    elif result["status"] == "low_confidence":
        await message.reply(
            "Nepodarilo sa presne precitat hodnotu z fotky.\n"
            "Prosim, zadaj hodnotu manualne prikazom:\n"
            "<code>/energia_oprava [id] [hodnota]</code>",
            parse_mode="HTML",
        )
    else:
        await message.reply(
            f"Chyba pri spracovani fotky: {result.get('error', 'neznama chyba')}"
        )


# --- Callback handlers ---

@router.callback_query(EnergyReadingAction.filter(F.action == "confirm"))
async def confirm_reading(callback: CallbackQuery, callback_data: EnergyReadingAction):
    await callback.answer("Odcit potvrdeny!")
    await callback.message.edit_reply_markup(reply_markup=None)


@router.callback_query(EnergyReadingAction.filter(F.action == "correct"))
async def correct_reading(callback: CallbackQuery, callback_data: EnergyReadingAction):
    await callback.answer()
    await callback.message.reply(
        f"Na opravu odcitu pouzi:\n"
        f"<code>/energia_oprava {callback_data.reading_id} [nova_hodnota]</code>",
        parse_mode="HTML",
    )


# --- Commands ---

@router.message(Command("energia_oprava"))
async def cmd_energy_correct(message: Message, session: AsyncSession):
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("Pouzitie: /energia_oprava <id> <nova_hodnota>")
        return

    try:
        reading_id = int(parts[1])
        new_value = float(parts[2].replace(",", "."))
    except ValueError:
        await message.answer("Nespravny format. Pouzitie: /energia_oprava <id> <hodnota>")
        return

    reading = await energy_repo.update_reading_value(session, reading_id, new_value)
    if reading:
        await message.answer(
            f"Odcit #{reading_id} opraveny na {format_number(new_value)} {reading.meter.unit}"
        )
    else:
        await message.answer(f"Odcit #{reading_id} nebol najdeny.")


@router.message(Command("energia_historia"))
async def cmd_energy_history(message: Message, session: AsyncSession):
    args = message.text.split()
    meters = await energy_repo.get_all_meters(session)

    if not meters:
        await message.answer("Zatial nie su zaregistrovane ziadne merace.")
        return

    # If meter name specified, show that one; otherwise show all
    if len(args) > 1:
        meter_name = " ".join(args[1:])
        meter = await energy_repo.get_meter_by_name(session, meter_name)
        if not meter:
            names = ", ".join(m.name for m in meters)
            await message.answer(f"Merac '{meter_name}' nebol najdeny.\nDostupne: {names}")
            return
        target_meters = [meter]
    else:
        target_meters = meters

    lines = ["<b>Historia odcitov:</b>\n"]
    for meter in target_meters:
        readings = await energy_repo.get_readings_for_meter(session, meter.id, limit=5)
        lines.append(f"\n<b>{meter.name}</b> ({meter.unit}):")
        if not readings:
            lines.append("  Zatial ziadne odcity")
        for r in readings:
            diff = f" (rozdiel: {format_number(r.difference)})" if r.difference is not None else ""
            lines.append(f"  {format_date(r.reading_date)}: {format_number(r.reading_value)}{diff}")

    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("energia_merace"))
async def cmd_energy_meters(message: Message, session: AsyncSession):
    meters = await energy_repo.get_all_meters(session)
    if not meters:
        await message.answer(
            "Zatial nie su zaregistrovane ziadne merace.\n"
            "Pouzi /energia_novy_merac na pridanie."
        )
        return

    lines = ["<b>Zaregistrovane merace:</b>\n"]
    type_sk = {"electricity": "Elektrina", "gas": "Plyn", "water": "Voda"}
    for m in meters:
        lines.append(
            f" <b>{m.name}</b> | {type_sk.get(m.meter_type, m.meter_type)} | {m.unit}"
            + (f" | {m.location}" if m.location else "")
        )
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("energia_novy_merac"))
async def cmd_new_meter(message: Message, session: AsyncSession, db_user: User):
    if db_user.telegram_id not in settings.admin_ids:
        await message.answer("Tento prikaz je len pre adminov.")
        return

    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer(
            "Pouzitie: /energia_novy_merac <typ> <nazov>\n"
            "Typy: electricity, gas, water\n"
            "Priklad: /energia_novy_merac electricity Elektromer hlavna budova"
        )
        return

    meter_type = parts[1].lower()
    name = parts[2]
    units = {"electricity": "kWh", "gas": "m³", "water": "m³"}

    if meter_type not in units:
        await message.answer("Nespravny typ. Pouzi: electricity, gas, water")
        return

    existing = await energy_repo.get_meter_by_name(session, name)
    if existing:
        await message.answer(f"Merac '{name}' uz existuje.")
        return

    meter = await energy_repo.create_meter(
        session, name=name, meter_type=meter_type, unit=units[meter_type]
    )
    await message.answer(f"Merac '{meter.name}' ({meter.unit}) bol zaregistrovany.")


@router.message(Command("energia_report"))
async def cmd_energy_report(message: Message, session: AsyncSession):
    meters = await energy_repo.get_all_meters(session)
    if not meters:
        await message.answer("Zatial nie su zaregistrovane ziadne merace.")
        return

    lines = ["<b>Prehlad poslednych odcitov:</b>\n"]
    for meter in meters:
        last = await energy_repo.get_last_reading(session, meter.id)
        if last:
            diff = f" | rozdiel: {format_number(last.difference)} {meter.unit}" if last.difference else ""
            lines.append(
                f"<b>{meter.name}</b>: {format_number(last.reading_value)} {meter.unit}"
                f" ({format_date(last.reading_date)}){diff}"
            )
        else:
            lines.append(f"<b>{meter.name}</b>: zatial ziadny odcit")

    await message.answer("\n".join(lines), parse_mode="HTML")
