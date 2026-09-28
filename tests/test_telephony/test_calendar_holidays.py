from datetime import date

from src.agents.anna.calendar.holidays import public_holidays


def test_all_twelve_baden_wuerttemberg_holidays_2026():
    assert public_holidays(2026) == {
        date(2026, 1, 1), date(2026, 1, 6), date(2026, 4, 3),
        date(2026, 4, 6), date(2026, 5, 1), date(2026, 5, 14),
        date(2026, 5, 25), date(2026, 6, 4), date(2026, 10, 3),
        date(2026, 11, 1), date(2026, 12, 25), date(2026, 12, 26),
    }


def test_computus_handles_early_late_and_century_easter():
    assert date(2008, 3, 21) in public_holidays(2008)  # Early Good Friday.
    assert date(2038, 4, 23) in public_holidays(2038)  # Latest Good Friday.
    assert date(2100, 3, 26) in public_holidays(2100)  # Non-leap century.
    assert date(2026, 10, 2) not in public_holidays(2026)
