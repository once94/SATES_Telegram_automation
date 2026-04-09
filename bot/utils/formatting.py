from datetime import datetime, date


def format_date(d: date | datetime | None) -> str:
    if d is None:
        return "—"
    if isinstance(d, datetime):
        return d.strftime("%d.%m.%Y %H:%M")
    return d.strftime("%d.%m.%Y")


def format_number(value: float) -> str:
    if value == int(value):
        return f"{int(value):,}".replace(",", " ")
    return f"{value:,.2f}".replace(",", " ")


def get_week_year(d: date | None = None) -> str:
    if d is None:
        d = date.today()
    iso = d.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def get_previous_week_year(d: date | None = None) -> str:
    if d is None:
        d = date.today()
    from datetime import timedelta

    prev = d - timedelta(weeks=1)
    iso = prev.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"
