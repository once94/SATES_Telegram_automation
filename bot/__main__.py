import asyncio
import logging

from bot.config import settings
from bot.db.base import Base, engine
from bot.db import models  # noqa: F401 - registruje vsetky modely na Base.metadata
from bot.loader import create_bot, create_dispatcher
from bot.scheduler.setup import create_scheduler

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    bot = create_bot()
    dp = create_dispatcher()
    scheduler = create_scheduler(bot)

    async def on_startup():
        scheduler.start()
        if settings.TOPIC_ENERGY == 0:
            logger.warning("TOPIC_ENERGY nie je nakonfigurovany (=0). Energy handler je neaktivny. Pouzi /discover_topics.")
        if settings.TOPIC_AUDITS == 0:
            logger.warning("TOPIC_AUDITS nie je nakonfigurovany (=0). Audit handler je neaktivny. Pouzi /discover_topics.")
        me = await bot.get_me()
        logger.info("Bot started: @%s", me.username)

    async def on_shutdown():
        scheduler.shutdown(wait=False)
        logger.info("Bot stopped.")

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
