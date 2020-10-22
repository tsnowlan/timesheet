from collections import namedtuple
import datetime
import sys

from .constants import TODAY


def ensure_db(db):
    def decorator(func):
        def inner(*args, **kwargs):
            db.ensure_db()
            return func(*args, **kwargs)

        return inner

    return decorator


def log_date(log_line: str):
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


def validate_action(ctx, param, value):
    if value.lower() in ("in", "out"):
        return value.lower()
    raise ValueError("You can only clock in or clock out")


def validate_datetime(ctx, param, dt: datetime.datetime):
    # replace default date on time string parse with today's date
    if dt.date() == datetime.date(1900, 1, 1):
        dt = dt.replace(year=TODAY.year, month=TODAY.month, day=TODAY.day)
    # strip seconds
    return dt.replace(second=0, microsecond=0)


Log = namedtuple(
    "Log",
    (
        "day",
        "type",
        "time",
    ),
)