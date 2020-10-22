from collections import namedtuple
import datetime
import gzip
from pathlib import Path
import sqlalchemy.exc
import sys

from .constants import UNLOCK_STR, LOGIN_STR, SHUTDOWN_STR, LIDCLOSE_STR
from .db import DB
from .models import Timesheet
from .util import log_date, ensure_db, Log

# exported objects
db = DB()

# exported functions
@ensure_db(db)
def get_day(day: datetime.date) -> Timesheet:
    try:
        day_log = db.session.query(Timesheet).filter(Timesheet.date == day).scalar()
    except Exception as e:
        breakpoint()
        raise e
    return day_log


@ensure_db(db)
def get_range(from_day: datetime.date, until_day: datetime.date) -> list[Timesheet]:
    try:
        logs = (
            db.session.query(Timesheet)
            .filter(Timesheet.date >= from_day, Timesheet.date < until_day)
            .order_by(Timesheet.date)
            .all()
        )
    except Exception as e:
        breakpoint()
        raise e
    return logs


@ensure_db(db)
def add_log(log_type: str, log_day: datetime.date, log_time: datetime.time) -> Log:
    log_data = {
        "day": log_day,
        "clock_in": log_time if log_type == "in" else None,
        "clock_out": log_time if log_type == "out" else None,
    }
    if row_exists(log_day):
        new_row = update_row(**log_data)
    else:
        new_row = add_row(**log_data)
    return new_row.log(log_type)


@ensure_db(db)
def edit_log(log_type: str, log_day: datetime.date, log_time: datetime.time) -> Log:
    log_data = {
        "day": log_day,
        f"clock_{log_type}": log_time,
    }
    if row_exists(log_day):
        new_row = update_row(**log_data)
    else:
        print(f"No existing logs on {log_day}", file=sys.stderr)
        sys.exit(1)
    return new_row.log("in")


@ensure_db(db)
def guess_day(day: datetime.date) -> Log:
    entries = list()
    for logfile in get_logs():
        log_activity = get_activity(logfile, day)
        entries.extend(log_activity["in"])
    if len(entries) == 0:
        print(f"Unable to find any logins on {day}", file=sys.stderr)
        sys.exit(1)
    return add_log("in", entries[0].date(), entries[0].time())


### internal stuff


def get_activity(
    logfile: Path, day: datetime.date = None, log_in=True, log_out=False
) -> list[datetime.datetime]:
    results = {"in": [], "out": []}
    open_func = open
    if logfile.name.endswith(".gz"):
        open_func = gzip.open
    with open_func(logfile, "rt") as logs:
        for log_line in logs:
            line_dt = log_date(log_line)
            # if no day passed, get all activity from file
            if day:
                # break out of files that won't have the day being looked for
                # skip lines that aren't on the day we're looking for
                if line_dt.date() > day:
                    break
                elif line_dt.date() < day:
                    continue
            if log_in and (LOGIN_STR in log_line or UNLOCK_STR in log_line):
                results["in"].append(line_dt)
            if log_out and (LIDCLOSE_STR in log_line or SHUTDOWN_STR in log_line):
                results["out"].append(line_dt)
    return results


def get_logs() -> list[Path]:
    log_dir = Path("/var/log")
    return log_dir.glob("auth.log*")


def row_exists(idx: datetime.date) -> bool:
    return bool(db.session.query(Timesheet).filter(Timesheet.date == idx).count())


def add_row(
    day: datetime.date,
    clock_in: datetime.time = None,
    clock_out: datetime.time = None,
) -> Timesheet:
    if not any([clock_in, clock_out]):
        raise ValueError("You must specify at ")
    new_row = Timesheet(date=day, clock_in=clock_in, clock_out=clock_out)
    try:
        db.session.add(new_row)
        db.session.commit()
    except sqlalchemy.exc.IntegrityError as e:
        db.session.rollback()
        if "UNIQUE constraint failed" in str(e):
            print(
                f"Cannot create duplicate log entry for {day}",
                file=sys.stderr,
            )
            sys.exit(1)
        else:
            raise (e)
    return new_row


def update_row(
    day: datetime.date,
    clock_in: datetime.time = None,
    clock_out: datetime.time = None,
    overwrite=False,
) -> Timesheet:
    row = db.session.query(Timesheet).filter(Timesheet.date == day).scalar()

    bail = list()
    if clock_in:
        if not row.clock_in or overwrite:
            row.clock_in = clock_in
        else:
            bail.append("clock_in")
    if clock_out:
        if not row.clock_out or overwrite:
            row.clock_out = clock_out
        else:
            bail.append("clock_out")

    if len(bail):
        info_str = ", ".join(
            [f"{k.replace('_', ' ')} ({getattr(row, k)})" for k in bail]
        )
        print(
            f"Not overwriting existing log{'s' if len(bail) > 1 else ''} on {day} for {info_str}",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        db.session.add(row)
        db.session.commit()
    except sqlalchemy.exc.SQLAlchemyError as e:
        breakpoint()
        raise e

    return row