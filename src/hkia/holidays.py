"""Hong Kong general holidays (verified against https://www.gov.hk/en/about/abouthk/holiday/2026.htm on 2026-08-17).

Only 2026 is needed for the current 91-day flight window; extend the dict when the data spans other years.
"""
import datetime as dt

HK_HOLIDAYS: dict[int, dict[dt.date, str]] = {
    2026: {
        dt.date(2026, 1, 1): "The first day of January",
        dt.date(2026, 2, 17): "Lunar New Year's Day",
        dt.date(2026, 2, 18): "The second day of Lunar New Year",
        dt.date(2026, 2, 19): "The third day of Lunar New Year",
        dt.date(2026, 4, 3): "Good Friday",
        dt.date(2026, 4, 4): "The day following Good Friday",
        dt.date(2026, 4, 6): "The day following Ching Ming Festival",
        dt.date(2026, 4, 7): "The day following Easter Monday",
        dt.date(2026, 5, 1): "Labour Day",
        dt.date(2026, 5, 25): "The day following the Birthday of the Buddha",
        dt.date(2026, 6, 19): "Tuen Ng Festival",
        dt.date(2026, 7, 1): "HKSAR Establishment Day",
        dt.date(2026, 9, 26): "The day following the Chinese Mid-Autumn Festival",
        dt.date(2026, 10, 1): "National Day",
        dt.date(2026, 10, 19): "The day following Chung Yeung Festival",
        dt.date(2026, 12, 25): "Christmas Day",
        dt.date(2026, 12, 26): "The first weekday after Christmas Day",
    },
}


def is_holiday(d: dt.date) -> bool:
    """True for HK general holidays (Sundays are NOT counted here; use day-of-week for that)."""
    return d in HK_HOLIDAYS.get(d.year, {})


def holiday_dates() -> set[dt.date]:
    return {d for year in HK_HOLIDAYS.values() for d in year}
