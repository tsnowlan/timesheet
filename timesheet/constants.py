import datetime
from enum import Enum
from pathlib import Path
from typing import Union


# dates
TODAY = datetime.date.today()
TOMORROW = TODAY + datetime.timedelta(days=1)
YESTERDAY = TODAY - datetime.timedelta(days=1)

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
VALID_CONFIG_FORMATS = {
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
}


# parameter defaults
DEF_DBFILE = Path().home() / "timesheet2.db"

# magic enums for better param validation
# typeshed stubs can't handle functional creation, so must hardcode for now :(
# LogType = TextEnum(
#     "LogType", {lt.upper(): f"clock_{lt}" for lt in VALID_LOG_TYPES}, module=__name__
# )
# TargetDay = TextEnum("TargetDay", {k: k.lower() for k in TARGET_DAYS}, module=__name__)
# TargetPeriod = TextEnum(
#     "TargetPeriod", {k: k.lower() for k in TARGET_PERIODS}, module=__name__
# )
# ConfigFormat = TextEnum(
#     "ConfigFormat",
#     {k[1:]: v for k, v in VALID_CONFIG_FORMATS.items()},
#     module=__name__,
# )
class Month(int, Enum):
    january = 1
    february = 2
    march = 3
    april = 4
    may = 5
    june = 6
    july = 7
    august = 8
    september = 9
    october = 10
    november = 11
    december = 12


class LogType(str, Enum):
    IN = "clock_in"
    OUT = "clock_out"


class TargetDay(str, Enum):
    today = "today"
    yesterday = "yesterday"


class TargetPeriod(str, Enum):
    all = "all"
    month = "month"
    lastmonth = "lastmonth"
    january = "january"
    february = "february"
    march = "march"
    april = "april"
    may = "may"
    june = "june"
    july = "july"
    august = "august"
    september = "september"
    october = "october"
    november = "november"
    december = "december"


class ConfigFormat(str, Enum):
    json = "json"
    yaml = "yaml"
    yml = "yaml"
    toml = "toml"


AllTargetsType = Union[TargetDay, TargetPeriod]
AllTargets: list[str] = [t.name for t in TargetDay] + [t.name for t in TargetPeriod]