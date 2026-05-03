"""
Calendar and event detection for ES trading context.
Handles: FOMC dates, OPEX Fridays, quarter-end, economic calendar.
No API required for historical flags; Finnhub free for upcoming events.
"""
from datetime import date, datetime, timedelta
from typing import Optional
import calendar
import pytz

ET = pytz.timezone("America/New_York")

# Hardcoded US market holidays 2010-2030
MARKET_HOLIDAYS = {
    # Format: "YYYY-MM-DD"
    "2010": ["2010-01-01","2010-01-18","2010-02-15","2010-04-02","2010-05-31",
             "2010-07-05","2010-09-06","2010-11-25","2010-12-24"],
    "2011": ["2011-01-17","2011-02-21","2011-04-22","2011-05-30","2011-07-04",
             "2011-09-05","2011-11-24","2011-12-26"],
    "2012": ["2012-01-02","2012-01-16","2012-02-20","2012-04-06","2012-05-28",
             "2012-07-04","2012-09-03","2012-11-22","2012-12-25"],
    "2013": ["2013-01-01","2013-01-21","2013-02-18","2013-03-29","2013-05-27",
             "2013-07-04","2013-09-02","2013-11-28","2013-12-25"],
    "2014": ["2014-01-01","2014-01-20","2014-02-17","2014-04-18","2014-05-26",
             "2014-07-04","2014-09-01","2014-11-27","2014-12-25"],
    "2015": ["2015-01-01","2015-01-19","2015-02-16","2015-04-03","2015-05-25",
             "2015-07-03","2015-09-07","2015-11-26","2015-12-25"],
    "2016": ["2016-01-01","2016-01-18","2016-02-15","2016-03-25","2016-05-30",
             "2016-07-04","2016-09-05","2016-11-24","2016-12-26"],
    "2017": ["2017-01-02","2017-01-16","2017-02-20","2017-04-14","2017-05-29",
             "2017-07-04","2017-09-04","2017-11-23","2017-12-25"],
    "2018": ["2018-01-01","2018-01-15","2018-02-19","2018-03-30","2018-05-28",
             "2018-07-04","2018-09-03","2018-11-22","2018-12-05","2018-12-25"],
    "2019": ["2019-01-01","2019-01-21","2019-02-18","2019-04-19","2019-05-27",
             "2019-07-04","2019-09-02","2019-11-28","2019-12-25"],
    "2020": ["2020-01-01","2020-01-20","2020-02-17","2020-04-10","2020-05-25",
             "2020-07-03","2020-09-07","2020-11-26","2020-12-25"],
    "2021": ["2021-01-01","2021-01-18","2021-02-15","2021-04-02","2021-05-31",
             "2021-07-05","2021-09-06","2021-11-25","2021-12-24"],
    "2022": ["2022-01-17","2022-02-21","2022-04-15","2022-05-30","2022-06-20",
             "2022-07-04","2022-09-05","2022-11-24","2022-12-26"],
    "2023": ["2023-01-02","2023-01-16","2023-02-20","2023-04-07","2023-05-29",
             "2023-07-04","2023-09-04","2023-11-23","2023-12-25"],
    "2024": ["2024-01-01","2024-01-15","2024-02-19","2024-03-29","2024-05-27",
             "2024-07-04","2024-09-02","2024-11-28","2024-12-25"],
    "2025": ["2025-01-01","2025-01-20","2025-02-17","2025-04-18","2025-05-26",
             "2025-07-04","2025-09-01","2025-11-27","2025-12-25"],
    "2026": ["2026-01-01","2026-01-19","2026-02-16","2026-04-03","2026-05-25",
             "2026-07-03","2026-09-07","2026-11-26","2026-12-25"],
    "2027": ["2027-01-01","2027-01-18","2027-02-15","2027-04-02","2027-05-31",
             "2027-07-05","2027-09-06","2027-11-25","2027-12-24"],
    "2028": ["2028-01-17","2028-02-21","2028-04-14","2028-05-29","2028-07-04",
             "2028-09-04","2028-11-23","2028-12-25"],
    "2029": ["2029-01-01","2029-01-15","2029-02-19","2029-03-30","2029-05-28",
             "2029-07-04","2029-09-03","2029-11-22","2029-12-25"],
    "2030": ["2030-01-01","2030-01-21","2030-02-18","2030-04-19","2030-05-27",
             "2030-07-04","2030-09-02","2030-11-28","2030-12-25"],
}

# FOMC meeting dates (approximate — announcement day) 2015-2026
FOMC_DATES = {
    "2015": ["2015-01-28","2015-03-18","2015-04-29","2015-06-17","2015-07-29",
             "2015-09-17","2015-10-28","2015-12-16"],
    "2016": ["2016-01-27","2016-03-16","2016-04-27","2016-06-15","2016-07-27",
             "2016-09-21","2016-11-02","2016-12-14"],
    "2017": ["2017-02-01","2017-03-15","2017-05-03","2017-06-14","2017-07-26",
             "2017-09-20","2017-11-01","2017-12-13"],
    "2018": ["2018-01-31","2018-03-21","2018-05-02","2018-06-13","2018-08-01",
             "2018-09-26","2018-11-08","2018-12-19"],
    "2019": ["2019-01-30","2019-03-20","2019-05-01","2019-06-19","2019-07-31",
             "2019-09-18","2019-10-30","2019-12-11"],
    "2020": ["2020-01-29","2020-03-03","2020-03-15","2020-04-29","2020-06-10",
             "2020-07-29","2020-09-16","2020-11-05","2020-12-16"],
    "2021": ["2021-01-27","2021-03-17","2021-04-28","2021-06-16","2021-07-28",
             "2021-09-22","2021-11-03","2021-12-15"],
    "2022": ["2022-01-26","2022-03-16","2022-05-04","2022-06-15","2022-07-27",
             "2022-09-21","2022-11-02","2022-12-14"],
    "2023": ["2023-02-01","2023-03-22","2023-05-03","2023-06-14","2023-07-26",
             "2023-09-20","2023-11-01","2023-12-13"],
    "2024": ["2024-01-31","2024-03-20","2024-05-01","2024-06-12","2024-07-31",
             "2024-09-18","2024-11-07","2024-12-18"],
    "2025": ["2025-01-29","2025-03-19","2025-05-07","2025-06-18","2025-07-30",
             "2025-09-17","2025-11-07","2025-12-10"],
    "2026": ["2026-01-28","2026-03-18","2026-04-29","2026-06-17","2026-07-29",
             "2026-09-16","2026-10-28","2026-12-16"],
}

# Build flat sets for fast O(1) lookup
ALL_HOLIDAYS: set = set()
ALL_FOMC: set = set()
for dates in MARKET_HOLIDAYS.values():
    ALL_HOLIDAYS.update(dates)
for dates in FOMC_DATES.values():
    ALL_FOMC.update(dates)


def is_market_holiday(d: date) -> bool:
    return d.strftime("%Y-%m-%d") in ALL_HOLIDAYS


def is_fomc_day(d: date) -> bool:
    return d.strftime("%Y-%m-%d") in ALL_FOMC


def is_fomc_eve(d: date) -> bool:
    next_day = d + timedelta(days=1)
    # Skip weekends
    while next_day.weekday() >= 5:
        next_day += timedelta(days=1)
    return is_fomc_day(next_day)


def is_opex_friday(d: date) -> bool:
    """Third Friday of the month = monthly options expiration."""
    if d.weekday() != 4:  # Not Friday
        return False
    # Count Fridays in month
    day_count = 0
    for day in range(1, d.day + 1):
        test_date = date(d.year, d.month, day)
        if test_date.weekday() == 4:
            day_count += 1
    return day_count == 3


def is_quarter_end(d: date) -> bool:
    """Last trading day of March, June, September, December."""
    if d.month not in (3, 6, 9, 12):
        return False
    # Check if next business day is in next month
    next_bd = d + timedelta(days=1)
    while next_bd.weekday() >= 5 or is_market_holiday(next_bd):
        next_bd += timedelta(days=1)
    return next_bd.month != d.month


def is_expiry_week(d: date) -> bool:
    """Week containing the third Friday."""
    # Find the third Friday
    first_day = date(d.year, d.month, 1)
    friday_count = 0
    third_friday = None
    for day in range(1, 32):
        try:
            test = date(d.year, d.month, day)
        except ValueError:
            break
        if test.weekday() == 4:
            friday_count += 1
            if friday_count == 3:
                third_friday = test
                break

    if third_friday is None:
        return False

    monday = third_friday - timedelta(days=4)
    return monday <= d <= third_friday


def get_prior_trading_day(d: date) -> date:
    """Get the prior valid trading session date (handles weekends, holidays, Monday-after-holiday)."""
    prev = d - timedelta(days=1)
    while prev.weekday() >= 5 or is_market_holiday(prev):
        prev -= timedelta(days=1)
    return prev


def get_calendar_flags(d: date) -> dict:
    """Return all calendar flags for a given date."""
    date_str = d.strftime("%Y-%m-%d")
    return {
        "date": date_str,
        "day_of_week": d.weekday(),  # 0=Monday
        "day_name": d.strftime("%A"),
        "month": d.month,
        "week_of_month": (d.day - 1) // 7 + 1,
        "is_fomc_day": is_fomc_day(d),
        "is_fomc_eve": is_fomc_eve(d),
        "is_opex_friday": is_opex_friday(d),
        "is_quarter_end": is_quarter_end(d),
        "is_expiry_week": is_expiry_week(d),
        "is_holiday": is_market_holiday(d),
    }


def get_week_of_month(d: date) -> int:
    return (d.day - 1) // 7 + 1
