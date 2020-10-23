import datetime
import sys
from collections import namedtuple
from pathlib import Path
from typing import Any, Callable, Tuple

import click

from .constants import MONTHS, TODAY, VALID_TARGETS


def ensure_db(db: Path) -> Callable:
    def decorator(func: Callable) -> Callable:
        def inner(*args: list[Any], **kwargs: dict[Any]) -> Callable:
            db.ensure_db()
            return func(*args, **kwargs)

        return inner

    return decorator


def log_date(log_line: str) -> datetime.datetime:
    (month, day, clock, log) = log_line.split(None, 3)
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


def target2dt(target: str) -> Tuple[datetime.date]:
    if target in VALID_TARGETS[:2]:
        return (TODAY if target == "today" else TODAY - datetime.timedelta(days=1), 0)
    elif target == "all":
        return (None, None)
    else:
        if target == "month":
            min_date = TODAY.replace(day=1)
            max_date = TODAY + datetime.timedelta(days=1)
            return (min_date, max_date)
        elif target == "lastmonth":
            min_date = (TODAY.replace(day=1) - datetime.timedelta(days=1)).replace(
                day=1
            )
        elif target in MONTHS:
            min_date = TODAY.replace(month=MONTHS[target], day=1)
        else:
            raise ValueError(f"Invalid target received: {target}")
        max_date = (
            min_date.replace(month=min_date.month + 1)
            if min_date.month < 12
            else datetime.date(year=min_date.year + 1, month=1, day=1)
        )
        return (min_date, max_date)


def validate_action(ctx: click.Context, param: click.Option, value: str) -> str:
    if value.lower() in ("in", "out"):
        return value.lower()
    raise ValueError("You can only clock in or clock out")


def validate_datetime(
    ctx: click.Context, param: click.Option, dt: datetime.datetime
) -> datetime.datetime:
    # replace default date on time string parse with today's date
    if dt.date() == datetime.date(1900, 1, 1):
        dt = dt.replace(year=TODAY.year, month=TODAY.month, day=TODAY.day)
    # strip seconds
    return dt.replace(second=0, microsecond=0)


def validate_target(ctx: click.Context, param: click.Argument, target: str) -> str:
    if target.lower() in VALID_TARGETS:
        return target.lower()
    print(
        f"\nInvalid {ctx.info_name} value: {target}.\n\nMust be one of: {', '.join(VALID_TARGETS)}\n",
        file=sys.stderr,
    )
    sys.exit(1)


Log = namedtuple(
    "Log",
    (
        "day",
        "type",
        "time",
    ),
)
