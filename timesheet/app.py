from collections import defaultdict
import datetime
import gzip
import sys
from pathlib import Path
from typing import Literal, Optional

import sqlalchemy.exc

from .constants import (
    LIDCLOSE_STR,
    LOGIN_STR,
    LOG_TYPES,
    SHUTDOWN_STR,
    UNLOCK_STR,
    TOMORROW,
)
from .db import DB
from .models import Timesheet
from .util import AuthLog, Log, ensure_db, log_date

# exported objects
db = DB()

# exported functions
@ensure_db(db)
def print_day(day: datetime.datetime) -> None:
    day_log = get_day(day)
    print(day_log)


@ensure_db(db)
def print_range(
    from_day: datetime.date, until_day: datetime.date, print_format: str = "print"
) -> None:
    logs_by_day = {l.date: l for l in get_range(from_day, until_day)}

    if print_format == "print":
        curr_day = from_day
        default_time = "None"
        while curr_day < until_day:
            if curr_day in logs_by_day:
                print(logs_by_day[curr_day])
            elif curr_day.weekday() > 4:
                print(curr_day)
            else:
                print(f"{curr_day}\t{default_time : <8}\t{default_time : <8}")
            curr_day += datetime.timedelta(days=1)
    else:
        raise NotImplemented()


@ensure_db(db)
def print_all() -> None:
    last_row = None
    for row in db.session.query(Timesheet).order_by(Timesheet.date):
        if last_row and last_row.date.month != row.date.month:
            print()
        print(row)
        last_row = row


@ensure_db(db)
def add_log(
    log_day: datetime.date, log_type: LOG_TYPES, log_time: datetime.time
) -> Log:
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
def edit_log(
    log_day: datetime.date, log_type: LOG_TYPES, log_time: datetime.time
) -> Log:
    log_data = {
        "day": log_day,
        f"clock_{log_type}": log_time,
    }
    if row_exists(log_day):
        new_row = update_row(**log_data)
    else:
        other_type = "clock_in" if log_type == "out" else "clock_out"
        log_data[other_type] = None
        print(f"No existing logs on {log_day}", file=sys.stderr)
        sys.exit(1)
    return new_row.log("in")


@ensure_db(db)
def guess_day(
    day: datetime.date,
    clock_in: bool = True,
    clock_out: bool = False,
    overwrite: bool = False,
) -> Log:
    # check for an existing entry and make sure we're not clobbering (unintentionally)
    day_log = get_day(day)
    if day_log:
        if clock_in and day_log.clock_in and not overwrite:
            raise RuntimeError(
                "Cannot guess for a clock in time when one is already set unless overwrite is used"
            )
        if clock_out and day_log.clock_out and not overwrite:
            raise RuntimeError(
                "Cannot guess for a clock out time when one is already set unless overwrite is used"
            )

    logins = list()
    logouts = list()
    for logfile in get_logs():
        log_activity = get_activity(logfile, day, clock_in, clock_out)
        if len(log_activity) == 0:
            continue

        if len(log_activity[day]["in"]):
            logins.extend(log_activity[day]["in"])

        if len(log_activity[day]["out"]):
            logouts.extend(log_activity[day]["out"])

    if len(logouts) == 0 and len(logins) == 0:
        print(f"Unable to find any activity on {day}", file=sys.stderr)
        sys.exit(1)

    row_info = {"date": day}
    if logins:
        row_info["clock_in"] = logins[0].time()
    if logouts:
        row_info["clock_out"] = logouts[-1].time()

    # make sure nothing wonky is happening
    if row_info.get("clock_in") and row_info.get("clock_out"):
        assert row_info["clock_in"] < row_info["clock_out"]

    if day_log:
        return update_row(**row_info)
    return add_row(**row_info)


@ensure_db(db)
def backfill_days(
    from_day: Optional[datetime.date] = None,
    until_day: Optional[datetime.date] = None,
    validate: Optional[bool] = False,
) -> list[Timesheet]:
    """
    Backfill entries in the given range based on auth.log activity.

    Days with activity and weekends are not
    """
    idx = index_logs()
    if len(index_logs) == 0:
        raise RuntimeError(
            f"Unable to read auth logs, check permission and log location"
        )
    if from_day is None:
        from_day = idx[0].min_date
    if until_day is None:
        until_day = TOMORROW

    new_days = list()
    curr_day = from_day
    while curr_day < until_day:

        curr_day += datetime.timedelta(days=1)

    return new_days


### internal stuff


def get_activity(
    logfile: Path, day: datetime.date, log_in=True, log_out=False
) -> defaultdict[datetime.date, dict[Literal["in", "out"], list[datetime.datetime]]]:
    results = defaultdict(lambda: {"in": [], "out": []})

    open_func = open
    if logfile.name.endswith(".gz"):
        open_func = gzip.open
    with open_func(logfile, "rt") as logs:
        for log_line in logs:
            line_dt = log_date(log_line)
            line_day = line_dt.day()

            # if no day passed, get all activity from file
            if day:
                # break out of files that won't have the day being looked for
                # skip lines that aren't on the day we're looking for
                if line_day > day:
                    break
                elif line_day < day:
                    continue
            if log_in and (LOGIN_STR in log_line or UNLOCK_STR in log_line):
                log_type = "in"
            elif log_out and (LIDCLOSE_STR in log_line or SHUTDOWN_STR in log_line):
                log_type = "out"
            else:
                continue

            results[line_day][log_type].append(line_dt)

    return results


def index_logs() -> list[AuthLog]:
    log_index = list()
    for logfile in get_logs():
        open_func = open
        if logfile.name.endswith(".gz"):
            open_func = gzip.open
        first_line = None
        last_line = None
        with open_func(logfile, "rt") as logs:
            for logline in logs:
                if not first_line:
                    first_line = logline
                last_line = logline
        if first_line == last_line == None:
            print(f"Encountered empty authlog {logfile}, skipping")
            continue
        first_day = log_date(first_line).date()
        last_day = log_date(last_line).date()
        log_index.append(AuthLog(logfile, first_day, last_day))
    # start from the oldest logs (auth.log.4.gz)
    log_index.reverse()
    return log_index


def get_day(day: datetime.date) -> Timesheet:
    try:
        day_log = db.session.query(Timesheet).filter(Timesheet.date == day).scalar()
    except Exception as e:
        breakpoint()
        raise e
    return day_log


def get_logs() -> list[Path]:
    log_dir = Path("/var/log")
    return log_dir.glob("auth.log*")


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


def row_exists(idx: datetime.date) -> bool:
    return bool(db.session.query(Timesheet).filter(Timesheet.date == idx).count())


def add_row(
    day: datetime.date,
    clock_in: Optional[datetime.time] = None,
    clock_out: Optional[datetime.time] = None,
    is_flex: Optional[bool] = False,
) -> Timesheet:
    if not any([clock_in, clock_out]):
        raise ValueError(
            "You must specify at least one time to create a new timesheet entry"
        )
    new_row = Timesheet(
        date=day, clock_in=clock_in, clock_out=clock_out, is_flex=is_flex
    )
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
