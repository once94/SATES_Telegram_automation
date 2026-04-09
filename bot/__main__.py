import asyncio
import logging

from bot.db.base import Base, engine
from bot.loader import create_bot, create_dispatcher
from bot.scheduler.setup import create_scheduler

logging.basicConfig(
    level=logging.INFO,
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
