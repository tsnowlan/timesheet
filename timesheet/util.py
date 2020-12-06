import datetime
import sys
from functools import wraps
from pathlib import Path
from typing import Callable, Iterable, NamedTuple, Optional, Union, overload

import click
from click.exceptions import BadParameter

from .constants import TODAY, TOMORROW, YESTERDAY
from .db import DB
from .enums import AllTargets, LogType, Month, TargetDay, TargetPeriod


@overload
def clean_time(dt_obj: datetime.datetime) -> datetime.datetime:
    ...


@overload
def clean_time(dt_obj: datetime.time) -> datetime.time:
    ...


def clean_time(dt_obj):
    "strips out seconds and partial seconds"
    return dt_obj.replace(second=0, microsecond=0)


def date_range(
    start: datetime.date, end: datetime.date, skip_weekends: bool = True
) -> Iterable[datetime.date]:
    while start < end:
        if start.weekday() < 5 or not skip_weekends:
            yield start
        start += datetime.timedelta(days=1)


def ensure_db(db: DB) -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def inner(*args, **kwargs):
            db._validate_conn()
            db._ensure_db()
            return func(*args, **kwargs)

        return inner

    return decorator


def log_date(log_line: str) -> datetime.datetime:
    (month, day, clock, _) = log_line.split(None, 3)
    try:
        dt = datetime.datetime.strptime(
            f"{datetime.date.today().year} {month} {day:0>2} {clock}",
            "%Y %b %d %H:%M:%S",
        )
    except ValueError as e:
        if "does not match format" in str(e):
            print(f"Could not parse date from log_line: {log_line}", file=sys.stderr)
            sys.exit(1)
        else:
            raise e
    return dt


def round_time(time_obj: datetime.time, thresh: int, to_nearest: int = 15) -> datetime.time:
    mod = time_obj.minute % to_nearest
    if mod == 0:
        return time_obj

    if mod <= thresh:
        rounded_time = datetime.timedelta(minutes=-mod)
    else:
        rounded_time = datetime.timedelta(minutes=to_nearest - mod)

    # throwaway dt object so we can use timedeltas for cleaner time math
    temp_dt = datetime.datetime.combine(TODAY, time_obj) + rounded_time
    return temp_dt.time()


def str2enum(
    ctx: click.Context, param: click.Parameter, value: str
) -> Union[LogType, TargetDay, TargetPeriod]:
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


def target2dt(
    target: Union[TargetPeriod, TargetDay],
) -> tuple[Optional[datetime.date], Optional[datetime.date]]:
    if target in (TargetDay.today, TargetDay.yesterday):
        min_date = TODAY if target.value == "today" else YESTERDAY
        max_date = min_date + datetime.timedelta(days=1)
        return (min_date, max_date)
    elif target == TargetPeriod.all:
        return (None, None)
    else:
        if target.value == "month":
            min_date = TODAY.replace(day=1)
            max_date = TOMORROW
            return (min_date, max_date)
        elif target.value == "lastmonth":
            min_date = (TODAY.replace(day=1) - datetime.timedelta(days=1)).replace(day=1)
        else:
            target_month = Month[target.value]
            min_date = TODAY.replace(month=target_month.value, day=1)
        max_date = (
            min_date.replace(month=min_date.month + 1)
            if min_date.month < 12
            else datetime.date(year=min_date.year + 1, month=1, day=1)
        )
        return (min_date, max_date)


def validate_datetime(
    ctx: click.Context, param: click.Parameter, dt: datetime.datetime
) -> datetime.datetime:
    # replace default date on time string parse with today's date
    if dt.date() == datetime.date(1900, 1, 1):
        dt = dt.replace(year=TODAY.year, month=TODAY.month, day=TODAY.day)
    # strip seconds
    return clean_time(dt.replace(second=0, microsecond=0))


class Log(NamedTuple):
    day: datetime.date
    type: LogType
    time: datetime.time


class AuthLog(NamedTuple):
    file: Path
    min_date: datetime.date
    max_date: datetime.date
