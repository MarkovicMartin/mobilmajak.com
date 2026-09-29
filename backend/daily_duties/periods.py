from datetime import date, timedelta

ACTIVE_PERIODS = ('daily', 'weekly', 'monthly')

PERIOD_LABELS = {
    'daily': 'Denně',
    'weekly': 'Týdně',
    'monthly': 'Měsíčně',
}

_MONTHS = (
    '', 'leden', 'únor', 'březen', 'duben', 'květen', 'červen',
    'červenec', 'srpen', 'září', 'říjen', 'listopad', 'prosinec',
)


def period_bounds(periodicity: str, day: date) -> tuple[date, date]:
    """Začátek a konec období, do kterého den spadá."""
    if periodicity == 'daily':
        return day, day
    if periodicity == 'weekly':
        start = day - timedelta(days=day.weekday())
        return start, start + timedelta(days=6)
    if periodicity == 'monthly':
        start = day.replace(day=1)
        if start.month == 12:
            next_month = start.replace(year=start.year + 1, month=1)
        else:
            next_month = start.replace(month=start.month + 1)
        return start, next_month - timedelta(days=1)
    raise ValueError(f'Nepodporovaná periodicita: {periodicity}')


def format_cz_date(day: date) -> str:
    return f'{day.day}. {day.month}. {day.year}'


def period_label(periodicity: str, start: date, end: date) -> str:
    if periodicity == 'daily':
        return format_cz_date(start)
    if periodicity == 'weekly':
        week = start.isocalendar()[1]
        return f'týden {week} ({format_cz_date(start)}–{format_cz_date(end)})'
    return f'{_MONTHS[start.month]} {start.year}'
