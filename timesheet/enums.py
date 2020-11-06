from enum import Enum, IntEnum, auto
from typing import Any, Union

# enums for nicer type checking of parameters and such
# unfortunately, the typeshed stubs can't process functional enum declarations, so need to have
# big, ugly, hardcoded blocks of text


class NamedEnum(str, Enum):
    @staticmethod
    def _generate_next_value_(
        name: str, start: int, count: int, last_values: list[Any]
    ) -> str:
        return name


class ConfigFormat(NamedEnum):
    json = auto()
    yaml = auto()
    yml = "yaml"
    toml = auto()


class Month(IntEnum):
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


# import calendar
# Month = IntEnum(
#     "Month",
#     [(name.lower(), i) for i, name in enumerate(calendar.month_name[1:], 1)]
#     + [(name.lower(), i) for i, name in enumerate(calendar.month_abbr[1:], 1)],
#     "module=__name__",
# )


class LogType(NamedEnum):
    IN = "clock_in"
    OUT = "clock_out"


class TargetDay(NamedEnum):
    today = auto()
    yesterday = auto()


class TargetPeriod(NamedEnum):
    all = auto()
    month = auto()
    lastmonth = auto()
    january = auto()
    jan = "january"
    february = auto()
    feb = february
    march = auto()
    mar = march
    april = auto()
    apr = april
    may = auto()
    june = auto()
    jun = june
    july = auto()
    jul = july
    august = auto()
    aug = august
    september = auto()
    sep = september
    october = auto()
    oct = october
    november = auto()
    nov = november
    december = auto()
    dec = december


# TargetPeriod = NamedEnum(
#     "TargetPeriod",
#     [d.name for d in TargetDay] + ["all"] + list(Month.__members__.keys()),
#     module=__name__,
# )


AllTargetsType = Union[TargetDay, TargetPeriod]
AllTargets: list[str] = [t.name for t in TargetDay] + [t.name for t in TargetPeriod]
