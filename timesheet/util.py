import datetime as DT
import logging
from pathlib import Path
from typing import Generator, Literal, NamedTuple, Optional, Union, overload

import click
from click.exceptions import BadParameter

from .constants import ONE_DAY, TODAY, TOMORROW, YESTERDAY
from .enums import AllTargets, LogType, Month, StrToEnum, TargetDay, TargetPeriod
from .types import OptionalDate, TimeDatetime


@overload
def clean_time(dt_obj: DT.datetime) -> DT.datetime:
    ...


@overload
def clean_time(dt_obj: DT.time) -> DT.time:
    ...


def clean_time(dt_obj: TimeDatetime):
    "strips out seconds and partial seconds"
    return dt_obj.replace(second=0, microsecond=0)


def date_range(start: DT.date, end: DT.date) -> Generator[DT.date, None, None]:
    while start < end:
        yield start
        start += ONE_DAY


def init_logs(log_level: int = logging.INFO, force: bool = False):
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(message)s",
        level=log_level,
        force=force,
    )


def log_date(log_line: str) -> DT.datetime:
    (month, day, clock, _) = log_line.split(None, 3)
    try:
        dt = DT.datetime.strptime(
            f"{DT.date.today().year} {month} {day:0>2} {clock}",
            "%Y %b %d %H:%M:%S",
        )
    except ValueError as e:
        if "does not match format" in str(e):
            logging.error(f"Could not parse date from log_line: '{log_line}'")
            logging.exception(e)
            exit(1)
        else:
            raise e
    return dt


def round_time(time_obj: DT.time, thresh: Optional[int] = None, to_nearest: int = 15) -> DT.time:
    if thresh is None:
        thresh = to_nearest // 2
    mod = time_obj.minute % to_nearest
    if mod == 0:
        return time_obj

    if mod <= thresh:
        rounded_time = DT.timedelta(minutes=-mod)
    else:
        rounded_time = DT.timedelta(minutes=to_nearest - mod)

    # throwaway dt object so we can use timedeltas for cleaner time math
    temp_dt = DT.datetime.combine(TODAY, time_obj) + rounded_time
    return temp_dt.time()


def dt2date(
    ctx: click.Context,
    param: click.Parameter,
    value: Optional[DT.datetime],
) -> Optional[DT.date]:
    if isinstance(value, DT.datetime):
        return value.date()
    return value


def str2enum(ctx: click.Context, param: click.Parameter, value: str) -> StrToEnum:
    if param.name == "log_type":
        try:
            new_enum = LogType(f"clock_{value}")
        except AttributeError:
            raise click.BadParameter(
                f"Invalid option for {param.name}. Must be one of: {', '.join([c.name.lower() for c in LogType])}"
            )
        return new_enum
    else:
        for enum_type in [TargetDay, TargetPeriod]:
            try:
                new_enum = enum_type[value.lower()]
            except KeyError:
                continue
            return new_enum
        raise BadParameter(
            f"Invalid option for {param.name}. Must be one of: {', '.join(AllTargets)}"
        )


def target2dt(target: Union[TargetPeriod, TargetDay]) -> tuple[OptionalDate, OptionalDate]:
    if target in (TargetDay.today, TargetDay.yesterday):
        min_date = TODAY if target.value == "today" else YESTERDAY
        max_date = min_date + ONE_DAY
        return (min_date, max_date)
    elif target == TargetPeriod.all:
        return (None, None)
    else:
        if target.value == "month":
            min_date = TODAY.replace(day=1)
            max_date = TOMORROW
            return (min_date, max_date)
        elif target.value == "lastmonth":
            min_date = (TODAY.replace(day=1) - ONE_DAY).replace(day=1)
        else:
            target_month = Month[target.name]
            min_date = TODAY.replace(month=target_month.value, day=1)
            # don't try and see the future
            if min_date > TODAY:
                min_date = min_date.replace(year=min_date.year - 1)
        max_date = (
            min_date.replace(month=min_date.month + 1)
            if min_date.month < 12
            else DT.date(year=min_date.year + 1, month=1, day=1)
        )
        return (min_date, max_date)


def time_difference(
    t1: DT.time,
    t2: DT.time,
    rounded: bool = False,
    round_threshold: Optional[int] = None,
) -> DT.timedelta:
    if rounded:
        thresh = round_threshold
        t1 = round_time(t1, thresh)
        t2 = round_time(t2, thresh)
    return abs(
        DT.datetime.strptime(str(t1), "%H:%M:%S") - DT.datetime.strptime(str(t2), "%H:%M:%S")
    )


def validate_datetime(ctx: click.Context, param: click.Parameter, dt: DT.datetime) -> DT.datetime:
    # replace default date on time string parse with today's date
    if dt.date() == DT.date(1900, 1, 1):
        dt = dt.replace(year=TODAY.year, month=TODAY.month, day=TODAY.day)
    # strip seconds
    return clean_time(dt.replace(second=0, microsecond=0))


class Log(NamedTuple):
    day: DT.date
    type: LogType
    time: Union[DT.time, Literal["Af"], Literal["Am"], None]


class AuthLog(NamedTuple):
    file: Path
    min_date: DT.date
    max_date: DT.date
