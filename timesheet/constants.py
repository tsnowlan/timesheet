import datetime
from pathlib import Path
from typing import Literal


# dates
TODAY = datetime.date.today()
TOMORROW = TODAY + datetime.timedelta(days=1)
YESTERDAY = TODAY - datetime.timedelta(days=1)
MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}

# formatting
TIME_FORMATS = ["%H:%M"]
for suffix in [":%S", ".%f"]:
    TIME_FORMATS.append(f"{TIME_FORMATS[-1]}{suffix}")
DATE_FORMATS = ["%Y-%m-%d"]
for tf in TIME_FORMATS:
    DATE_FORMATS.append(f"{DATE_FORMATS[0]} {tf}")
DATETIME_FORMATS = TIME_FORMATS + DATE_FORMATS
ROW_HEADER = f"{'date': <8}\t{'Clock In': <8}\t{'Clock Out': <8}"

# log parsing
LOGIN_STRS = (
    "Lid opened",
    "Operation 'sleep' finished",
    "unlocked login keyring",
    "gnome-keyring-daemon started properly and unlocked keyring",
)
LOGOUT_STRS = ("Lid closed", "System is powering down")

# parameter validation
VALID_TARGETS = ["today", "yesterday", "month", "lastmonth", "all"] + list(
    MONTHS.keys()
)
VALID_LOG_TYPES = ["in", "out"]
LOG_TYPES = Literal["in", "out"]

# parameter defaults
DEF_DBFILE = Path().home() / "timesheet2.db"
