from aiogram import Router


def get_main_router() -> Router:
    from bot.handlers import common, audits, energy, tasks, errors

    main_router = Router(name="main")
    main_router.include_routers(
        errors.router,
        common.router,
        tasks.router,
        audits.router,
        energy.router,
    )
    return main_router
