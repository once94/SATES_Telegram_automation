from aiogram import Router


def get_main_router() -> Router:
    from bot.handlers import common, audits, energy, tasks

    main_router = Router(name="main")
    main_router.include_routers(
        common.router,
        tasks.router,
        audits.router,
        energy.router,
    )
    return main_router
