"""Statutory Baden-Wuerttemberg holidays for ANNA's Berlin-time calendar."""

from datetime import date, timedelta
from functools import lru_cache


@lru_cache(maxsize=128)
def public_holidays(year: int) -> frozenset[date]:
    """Return fixed holidays and Easter-relative dates using Gregorian computus."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    weekday = (32 + 2 * e + 2 * i - h - k) % 7
    correction = (a + 11 * h + 22 * weekday) // 451
    month, day = divmod(h + weekday - 7 * correction + 114, 31)
    easter = date(year, month, day + 1)
    fixed = {(1, 1), (1, 6), (5, 1), (10, 3), (11, 1), (12, 25), (12, 26)}
    return frozenset(
        {date(year, month, day) for month, day in fixed}
        | {easter + timedelta(days=offset) for offset in (-2, 1, 39, 50, 60)}
    )
