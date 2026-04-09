from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder


class EnergyReadingAction(CallbackData, prefix="energy"):
    action: str  # "confirm", "correct"
    reading_id: int


class TaskAction(CallbackData, prefix="task"):
    action: str  # "done", "cancel"
    task_id: int


def energy_reading_keyboard(reading_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Potvrdit",
        callback_data=EnergyReadingAction(action="confirm", reading_id=reading_id),
    )
    builder.button(
        text="Opravit",
        callback_data=EnergyReadingAction(action="correct", reading_id=reading_id),
    )
    builder.adjust(2)
    return builder.as_markup()


def task_keyboard(task_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Hotovo",
        callback_data=TaskAction(action="done", task_id=task_id),
    )
    builder.button(
        text="Zrusit",
        callback_data=TaskAction(action="cancel", task_id=task_id),
    )
    builder.adjust(2)
    return builder.as_markup()
