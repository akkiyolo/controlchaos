"""Financial calendar, business day, and month-end accrual date utilities."""

import calendar
from datetime import date
from typing import List

GLOBAL_HOLIDAYS_FIXED = {
    (1, 1),   # New Year's Day
    (12, 25), # Christmas
    (12, 26), # Boxing Day
    (7, 4),   # US Independence Day
    (5, 1),   # Labour Day
}


def is_weekend(d: date) -> bool:
    """Returns True if date is Saturday (5) or Sunday (6)."""
    return d.weekday() >= 5


def is_holiday(d: date) -> bool:
    """Checks whether a date is a recognized global financial market holiday."""
    return (d.month, d.day) in GLOBAL_HOLIDAYS_FIXED


def is_business_day(d: date) -> bool:
    """Returns True if date is neither weekend nor holiday."""
    return not is_weekend(d) and not is_holiday(d)


def get_month_dates(year: int, month: int) -> List[date]:
    """Returns all dates in the given month."""
    _, num_days = calendar.monthrange(year, month)
    return [date(year, month, day) for day in range(1, num_days + 1)]


def get_month_business_days(year: int, month: int) -> List[date]:
    """Returns all business days in the given month."""
    return [d for d in get_month_dates(year, month) if is_business_day(d)]


def get_month_end_business_day(year: int, month: int) -> date:
    """Returns the last business day of the given month."""
    b_days = get_month_business_days(year, month)
    return b_days[-1] if b_days else date(year, month, 28)


def get_period_strings(start_period: str, num_months: int) -> List[str]:
    """
    Given '2025-01' and 12, returns list of period strings:
    ['2025-01', '2025-02', ..., '2025-12'].
    """
    start_year, start_month = map(int, start_period.split("-"))
    periods = []
    y, m = start_year, start_month
    for _ in range(num_months):
        periods.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m = 1
            y += 1
    return periods
