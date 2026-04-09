import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.config import settings
from bot.db.models.user import User

logger = logging.getLogger(__name__)
router = Router(name="common")


@router.message(Command("start"))
async def cmd_start(message: Message, db_user: User):
    await message.answer(
        f"Ahoj, {db_user.full_name}!\n\n"
        "Som SATES Automat - bot pre spravu firemnej skupiny.\n\n"
        "Moje hlavne funkcie:\n"
        " Automaticky rozpoznavam merače z fotiek\n"
        " Zbieram zaznamy z auditov a generujem tyzdenne reporty\n"
        " Spravujem ulohy a pripomienky\n\n"
        "Pouzi /help pre kompletny zoznam prikazov."
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "<b>SATES Automat - Prikazy</b>\n\n"
        "<b>Vseobecne:</b>\n"
        "/start - Uvitanie\n"
        "/help - Tento help\n"
        "/me - Tvoj profil\n\n"
        "<b>Ulohy (v kazdom topicu):</b>\n"
        "/uloha_nova @user text [termin:RRRR-MM-DD]\n"
        "/uloha_zoznam - Tvoje otvorene ulohy\n"
        "/uloha_hotovo &lt;id&gt; - Oznacit ulohu za hotovu\n"
        "/uloha_vsetky - Vsetky otvorene ulohy\n\n"
        "<b>Energia (topic Odpisy energii):</b>\n"
        " Posli fotku meraca - automaticky rozpoznam\n"
        "/energia_historia [merac] - Historia odcitov\n"
        "/energia_report [mesiac] - Mesacny prehlad\n"
        "/energia_merace - Zoznam meracov\n"
        "/energia_novy_merac &lt;nazov&gt; &lt;typ&gt; - Pridat merac\n\n"
        "<b>Audity (topic Audity a kontroly):</b>\n"
        " Posli fotku/text - ulozim pre tyzdenny report\n"
        "/audit_zoznam - Zoznam reportov\n"
        "/audit_report [tyzden] - Zobrazit report\n"
        "/audit_notifikacie - Zapnut/vypnut DM reporty\n\n"
        "<b>Admin:</b>\n"
        "/discover_topics - Zistit thread ID topicov",
        parse_mode="HTML",
    )


@router.message(Command("me"))
async def cmd_me(message: Message, db_user: User):
    role_sk = {"admin": "Admin", "manager": "Manazer", "member": "Clen"}
    audit_status = "zapnute" if db_user.receive_audit_reports else "vypnute"
    await message.answer(
        f"<b>Tvoj profil:</b>\n"
        f"Meno: {db_user.full_name}\n"
        f"Username: @{db_user.username or '—'}\n"
        f"Rola: {role_sk.get(db_user.role, db_user.role)}\n"
        f"Audit reporty DM: {audit_status}",
        parse_mode="HTML",
    )


@router.message(Command("discover_topics"))
async def cmd_discover_topics(message: Message, db_user: User):
    if db_user.telegram_id not in settings.ADMIN_TELEGRAM_IDS:
        await message.answer("Tento prikaz je len pre adminov.")
        return

    thread_id = message.message_thread_id
    if thread_id:
        await message.answer(
            f"<b>Topic info:</b>\n"
            f"Thread ID: <code>{thread_id}</code>\n\n"
            "Pouzi tento prikaz v kazdom topicu, aby si zistil jeho thread ID.\n"
            "Nastav ich v .env subore (TOPIC_AUDITS, TOPIC_ENERGY, ...)",
            parse_mode="HTML",
        )
    else:
        await message.answer(
            "Pouzi tento prikaz priamo v topicu (vlakne), aby si zistil jeho thread ID."
        )
