from collections import defaultdict
import datetime
import gzip
import sys
from pathlib import Path
from typing import Literal, Optional

import sqlalchemy.exc

from .constants import (
    LOGIN_STRS,
    LOGOUT_STRS,
    LOG_TYPES,
    ROW_HEADER,
    TOMORROW,
    VALID_LOG_TYPES,
)
from .db import DB
from .models import Timesheet
from .util import AuthLog, Log, clean_time, ensure_db, log_date

# exported objects
db = DB()

# exported functions
@ensure_db(db)
def print_day(day: datetime.datetime) -> None:
    day_log = get_day(day, False)
    print(ROW_HEADER)
    print(day_log)


@ensure_db(db)
def print_range(
    from_day: datetime.date, until_day: datetime.date, print_format: str = "print"
) -> None:
    logs_by_day = {l.date: l for l in get_range(from_day, until_day)}

    if print_format == "print":
        curr_day = from_day
        default_time = "None"
        print(ROW_HEADER)
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
    print(ROW_HEADER)
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
    validate: bool = False,
    overwrite: bool = False,
) -> list[Timesheet]:
    """
    Backfill entries on weekdays in the given range based on auth.log activity.

    Replacing existing data requires validate=True or overwrite=True
    """
    idx = index_logs()
    if len(idx) == 0:
        raise RuntimeError(
            f"Unable to read auth logs, check permission and log location"
        )
    if from_day is None:
        from_day = idx[0].min_date
    if until_day is None:
        until_day = TOMORROW
    print(f"Backfilling from {from_day} until {until_day}")

    all_activity = dict()
    for authlog in idx:
        if (from_day <= authlog.min_date and authlog.min_date < until_day) or (
            authlog.max_date >= from_day and authlog.max_date < until_day
        ):
            log_activity = get_activity(authlog.file, None, True, True)
            for log_day in log_activity:
                # skip any days outside of range or on the weekend
                if log_day < from_day or log_day >= until_day or log_day.weekday() > 4:
                    continue
                if log_day in all_activity:
                    for lt in VALID_LOG_TYPES:
                        all_activity[log_day][lt].extend(log_activity[log_day][lt])
                else:
                    all_activity[log_day] = log_activity[log_day]

    audit_list = list()
    for a_day, activity in all_activity.items():
        curr_row = get_day(a_day)
        clock_in = sorted(activity["in"])[0] if activity["in"] else None
        clock_out = sorted(activity["out"])[-1] if activity["out"] else None
        if curr_row:
            new_times = (
                clock_in if clock_in and clock_in != curr_row.clock_in else None,
                clock_out if clock_out and clock_out != curr_row.clock_out else None,
            )
            if any(new_times):
                audit_list.append((curr_row, new_times))
        else:
            new_row = Timesheet(date=a_day, clock_in=clock_in, clock_out=clock_out)
            audit_list.append((new_row, None))

    new_days = list()
    for (log_obj, updates) in audit_list:
        new_obj = merge_times(log_obj, updates, validate, overwrite)
        if new_obj:
            new_days.append(new_obj)

    if not new_days:
        return

    breakpoint()
    try:
        db.session.add_all(new_days)
        db.session.commit()
    except Exception as e:
        breakpoint()
        db.session.rollback()
        raise e

    return new_days


### internal stuff


def merge_times(
    current: Timesheet,
    new_times: tuple[int, int],
    validate: bool = False,
    overwrite: bool = False,
):
    if new_times:
        if validate:
            ci_str = f"in {current.clock_in}"
            if new_times[0]:
                ci_str += f" -> {new_times[0]}"
            co_str = f"out {current.clock_out}"
            if new_times[1]:
                co_str += f" -> {new_times[1]}"
            msg_str = f"Update existing data on {current.date}: {ci_str}, {co_str}"
            if not get_resp(msg_str):
                print(f"Skipping {current.date}")
                return
        else:
            # skip any existing values unless overwrite enabled
            skip = []
            if new_times[0] and current.clock_in and not overwrite:
                skip.append("clock_in")
            if new_times[1] and current.clock_out and not overwrite:
                skip.append("clock_out")

            if len(skip) == 2:
                # "new" times match or won't overwrite existing values
                return
            elif len(skip) == 1:
                # remove the one that got skipped
                new_times = (
                    new_times[0] if "clock_in" not in skip else None,
                    new_times[1] if "clock_out" not in skip else None,
                )
            # else leave new_times as is: two new values to update (unlikely unless overwrite)
    else:
        if validate and not get_resp(
            f"Create new entry on {current.date}: clock in {current.clock_in}, clock out {current.clock_out}"
        ):
            print(f"Skipping {current.date}")
            return

    if new_times and any(new_times):
        if new_times[0]:
            current.clock_in = new_times[0]
        if new_times[1]:
            current.clock_out = new_times[1]
    else:
        return
    return current


def get_resp(msg: str) -> bool:
    pos = ("y", "yes")
    neg = ("n", "no")
    resp = input(f"{msg}  [y/n] ").lower()
    while resp not in pos and resp not in neg:
        print(f"Invalid response. Choose [y]es or [n]o")
        resp = input(f"{msg}  [y/n] ").lower()
    return resp in pos


def get_activity(
    logfile: Path,
    day: Optional[datetime.date] = None,
    log_in: bool = True,
    log_out: bool = False,
) -> defaultdict[datetime.date, dict[Literal["in", "out"], list[datetime.datetime]]]:
    results = defaultdict(lambda: {"in": [], "out": []})

    open_func = open
    if logfile.name.endswith(".gz"):
        open_func = gzip.open
    with open_func(logfile, "rt") as logs:
        for log_line in logs:
            line_dt = log_date(log_line)
            line_day = line_dt.date()

            # if no day passed, get all activity from file
            if day:
                # break out of files that won't have the day being looked for
                # skip lines that aren't on the day we're looking for
                if line_day > day:
                    break
                elif line_day < day:
                    continue
            if log_in and any(
                [True for login_str in LOGIN_STRS if login_str in log_line]
            ):
                log_type = "in"
            elif log_out and any(
                [True for logout_str in LOGOUT_STRS if logout_str in log_line]
            ):
                log_type = "out"
            else:
                continue

            results[line_day][log_type].append(clean_time(line_dt.time()))

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
                # skip empty lines
                if not logline.strip():
                    continue

                if first_line is None:
                    first_line = logline
                last_line = logline
        if first_line is None:
            print(f"Encountered empty authlog {logfile}, skipping")
            continue
        min_date = log_date(first_line).date()
        max_date = log_date(last_line).date()
        log_index.append(AuthLog(logfile, min_date, max_date))
    # start from the oldest logs (auth.log.4.gz)
    return sorted(log_index, key=lambda x: x.min_date)


def get_day(day: datetime.date, missing_okay: bool = True) -> Timesheet:
    day_log = db.session.query(Timesheet).filter(Timesheet.date == day).scalar()
    if day_log is None and not missing_okay:
        raise RuntimeError(f"Unable to find timesheet entry for {day}")
    return day_log


def get_logs(log_dir: Path = Path("/var/log")) -> list[Path]:
    return log_dir.glob("auth.log*")


def get_range(
    from_day: datetime.date, until_day: datetime.date, missing_okay: bool = True
) -> list[Timesheet]:
    logs = (
        db.session.query(Timesheet)
        .filter(Timesheet.date >= from_day, Timesheet.date < until_day)
        .order_by(Timesheet.date)
        .all()
    )
    if len(logs) == 0 and not missing_okay:
        raise RuntimeError(
            f"No timesheet entries found from {from_day} until {until_day}"
        )
    return logs


def row_exists(idx: datetime.date) -> bool:
    return bool(get_day(idx))


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
        # something might happen?
        breakpoint()
        db.session.rollback()
        raise e

    return row
