import datetime
import gzip
import logging
from functools import wraps
from io import TextIOWrapper
from pathlib import Path
from typing import Callable, Iterable, List, Literal, Optional, Tuple

from sqlalchemy.exc import IntegrityError

from .config import Config
from .constants import ROW_HEADER, TODAY, TOMORROW
from .db import DB
from .enums import LogType
from .exceptions import ExistingData, NoData
from .models import FlexBalance, Holiday, Timesheet
from .util import AuthLog, Log, clean_time, date_range, log_date, round_time, time_difference

# log parsing
LOGIN_STRS = (
    "Lid opened",
    "Operation 'sleep' finished",
    "unlocked login keyring",
    "gnome-keyring-daemon started properly and unlocked keyring",
)
LOGOUT_STRS = ("Lid closed", "System is powering down")

# exported objects
db: DB = DB()
config: Config = Config()


def ensure_db(db: DB) -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def inner(*args, **kwargs):
            db._validate_conn()
            db._ensure_db()
            return func(*args, **kwargs)

        return inner

    return decorator


# exported functions
@ensure_db(db)
def print_range(
    from_day: Optional[datetime.date],
    until_day: Optional[datetime.date],
    print_format: Literal["print", "export"] = "print",
) -> None:
    logs_by_day = {l.date: l for l in get_range(from_day, until_day)}
    if len(logs_by_day) == 0:
        if from_day and until_day:
            raise NoData(
                db.db_file,
                "timesheet.date",
                f"No data found between {from_day} and {until_day}",
            )
        elif from_day:
            raise NoData(
                db.db_file, "timesheet.date", f"No data found between {from_day} and {TOMORROW}"
            )
        elif until_day:
            raise NoData(db.db_file, "timesheet.date", f"No data found before {TOMORROW}")
        else:
            raise NoData(db.db_file, "timesheet.date", f"No log entries found, table is empty")

    if from_day is None:
        from_day = sorted(logs_by_day.keys())[0]
    if until_day is None or until_day > TOMORROW:
        until_day = TOMORROW
    logging.debug(f"printing data from {from_day} until {until_day}")

    if print_format == "print":
        default_time = "None"
        print(ROW_HEADER)
        for curr_day in date_range(from_day, until_day, False):
            if curr_day in logs_by_day:
                print(logs_by_day[curr_day])
            elif not is_workday(curr_day):
                print(curr_day)
            else:
                print(f"{curr_day}\t{default_time : <8}\t{default_time : <8}")
    else:
        for log_type in LogType:
            print(f"{log_type.value.upper()}")
            print("=" * 10)
            for curr_day in date_range(from_day, until_day, False):
                if curr_day in logs_by_day:
                    day_log = logs_by_day[curr_day].log(log_type)
                    if isinstance(day_log.time, datetime.time):
                        rounded = round_time(
                            day_log.time,
                            config.round_threshold,
                        )
                        print(f"{rounded.hour:02}\t{rounded.minute:02}")
                    elif day_log.time is None:
                        print()
                    else:
                        print(day_log.time)
                else:
                    print()
            print()


@ensure_db(db)
def add_log(log_day: datetime.date, log_type: LogType, log_time: datetime.time) -> Log:
    log_data = {
        "day": log_day,
        "clock_in": log_time if log_type == LogType.IN else None,
        "clock_out": log_time if log_type == LogType.OUT else None,
    }
    if row_exists(log_day):
        new_row = update_row(**log_data)
    else:
        new_row = add_row(**log_data)
    return new_row.log(log_type)


@ensure_db(db)
def edit_log(log_day: datetime.date, log_type: LogType, log_time: datetime.time) -> Timesheet:
    log_data = {"day": log_day, log_type.value: log_time, "overwrite": True}
    if row_exists(log_day):
        new_row = update_row(**log_data)
    else:
        raise NoData(db.db_file, f"timesheet.date={log_day}")
    return new_row


@ensure_db(db)
def guess_day(
    day: datetime.date,
    clock_in: bool = True,
    clock_out: bool = False,
    overwrite: bool = False,
) -> Timesheet:
    # check for an existing entry
    day_log = get_day(day)

    logins: list[datetime.time] = list()
    logouts: list[datetime.time] = list()
    logfiles = get_logs()
    logging.debug(f"Found log files: {', '.join([str(s) for s in logfiles])}")
    for logfile in logfiles:
        logging.info(f"checking {logfile} for activity")
        log_activity = get_activity(logfile, day, clock_in, clock_out)
        if len(log_activity) == 0:
            continue

        if len(log_activity[day][LogType.IN]):
            logins.extend(log_activity[day][LogType.IN])

        if len(log_activity[day][LogType.OUT]):
            logouts.extend(log_activity[day][LogType.OUT])

    if len(logouts) == 0 and len(logins) == 0:
        logging.error(f"Unable to find any activity on {day}")
        exit(1)

    # have to do this extra explicitly so typing works
    in_time: Optional[datetime.time] = logins[0] if logins else None
    out_time: Optional[datetime.time] = logouts[-1] if logouts else None

    if in_time and day_log and day_log.clock_in and not overwrite:
        raise ExistingData((day_log, "clock_in"), in_time)

    if out_time and day_log and day_log.clock_out and not overwrite:
        raise ExistingData((day_log, "clock_out"), out_time)

    # make sure nothing wonky is happening
    if in_time and out_time:
        assert in_time < out_time

    if day_log:
        return update_row(day, in_time, out_time)
    return add_row(day, in_time, out_time)


@ensure_db(db)
def backfill_days(
    from_day: Optional[datetime.date] = None,
    until_day: Optional[datetime.date] = None,
    use_standard: bool = False,
    validate: bool = False,
    overwrite: bool = False,
) -> Optional[list[Timesheet]]:
    """
    Backfill entries on weekdays in the given range based on auth.log activity.

    Replacing existing data requires validate=True or overwrite=True
    """
    idx = index_logs()
    logging.debug(f"got indexed logs {idx}")
    if len(idx) == 0:
        err = RuntimeError(f"Unable to read auth logs, check permission and log location")
        if use_standard:
            logging.warning(f"{err}: Only filling standard days.")
        else:
            raise err

    if from_day is None:
        from_day = idx[0].min_date
    if until_day is None:
        until_day = TOMORROW
    logging.info(f"Backfilling from {from_day} until {until_day}")

    all_activity: dict[datetime.date, dict[LogType, list[datetime.time]]] = dict()
    for authlog in idx:
        # target range: [from_day, until_day)
        # log dates: [min_date, max_date]
        logging.debug(f"Checking {authlog.file} for activity")
        if (from_day <= authlog.min_date < until_day) or (
            from_day <= authlog.max_date <= until_day
        ):
            log_activity = get_activity(authlog.file, log_in=True, log_out=True)
            for log_day in log_activity:
                # skip any days outside of range and weekends/holidays
                if log_day < from_day or log_day >= until_day or is_holiday(log_day):
                    continue
                if log_day in all_activity:
                    logging.debug(f"extending new activity for {log_day}")
                    for lt in LogType:
                        all_activity[log_day][lt].extend(log_activity[log_day][lt])
                else:
                    logging.debug(f"adding new activity for {log_day}")
                    all_activity[log_day] = log_activity[log_day]

    new_days: list[Timesheet] = []
    AuditRow = Tuple[Timesheet, Tuple[Optional[datetime.time], Optional[datetime.time]]]
    audit_list: list[AuditRow] = list()
    for a_day in date_range(from_day, until_day):
        logging.debug(f"checking for activity from {a_day}")
        curr_row = get_day(a_day)
        if use_standard:
            clock_in = config.standard_start
            clock_out = config.standard_quit
        else:
            clock_in = None
            clock_out = None

        if a_day in all_activity:
            logging.debug(f"found activity on {a_day}")
            # get earliest login
            if all_activity[a_day][LogType.IN]:
                clock_in = sorted(all_activity[a_day][LogType.IN])[0]

            # get last logout
            if all_activity[a_day][LogType.OUT]:
                clock_out = sorted(all_activity[a_day][LogType.OUT])[-1]
        elif not use_standard:
            # not in log activity, not using standard, nothing to do here
            continue

        if curr_row:
            logging.debug(f"updating existing record {curr_row}")
            new_times = (
                clock_in if clock_in and clock_in != curr_row.clock_in else None,
                clock_out if clock_out and clock_out != curr_row.clock_out else None,
            )
            if any(new_times):
                audit_list.append((curr_row, new_times))
        else:
            new_row = Timesheet(date=a_day, clock_in=clock_in, clock_out=clock_out)
            logging.debug(f"creating new record {new_row}")
            if not validate or get_resp(
                f"Create new entry on {new_row.date}: clock in {new_row.clock_in}, clock out {new_row.clock_out}"
            ):
                new_days.append(new_row)

    for (log_obj, updates) in audit_list:
        new_obj = merge_times(log_obj, updates, validate, overwrite)
        if new_obj:
            new_days.append(new_obj)

    if len(new_days) == 0:
        return

    db.session.add_all(new_days)
    db.try_commit()
    return sorted(new_days, key=lambda x: x.date)


@ensure_db(db)
def import_calendar(cal: TextIOWrapper):
    """Parse an ics file and load into db"""
    in_event = False
    curr_event = dict()
    all_events = []
    for line in cal:
        if not in_event and line.strip() == "BEGIN:VEVENT":
            in_event = True
        elif in_event:
            key, val = line.strip().split(":", 1)
            if key == "SUMMARY":
                curr_event["name"] = val
            elif key == "DTSTART":
                curr_event["date"] = datetime.datetime.strptime(val, "%Y%m%d").date()
            elif key == "END":
                existing = (
                    db.session.query(Holiday)
                    .filter(
                        Holiday.date == curr_event["date"] and Holiday.name == curr_event["name"]
                    )
                    .all()
                )
                if existing:
                    logging.debug("{name} on {date} already exists, skipping".format(**curr_event))
                    continue
                logging.debug("Creating holiday '{name}' on {date}".format(**curr_event))
                hday = Holiday(**curr_event)
                all_events.append(hday)
                curr_event = dict()
                in_event = False
    db.session.add_all(all_events)
    db.try_commit(True)
    logging.info(f"Added {len(all_events)} new holidays to table")
    pass


@ensure_db(db)
def flex_date(dt: datetime.date, flex_val: bool = True) -> Timesheet:
    day = get_day(dt)
    if day:
        if flex_val == day.is_flex:
            logging.info(f"{dt} already has is_flex={flex_val}")
            return day
        elif flex_val:
            logging.warning(f"Existing, non-flex data on {dt} will be ignored")
    else:
        day = Timesheet(date=dt)
    day.is_flex = flex_val  # type: ignore
    db.session.add(day)
    db.try_commit(True)
    logging.info(f"Marked {dt} is_flex={flex_val}")
    return day


@ensure_db(db)
def get_flex_balance(dt: datetime.date) -> Tuple[FlexBalance, List[datetime.date]]:
    """returns flex balance for the given day and list of days missing entries (if any)"""
    missing_logs = []
    latest: Optional[FlexBalance] = (
        db.session.query(FlexBalance).order_by(FlexBalance.date.desc()).first()
    )
    if latest is None:
        raise NoData(
            db.db_file, "flexbalance", "No flex balance data, cannot fetch current balance"
        )
    elif latest.date == dt:
        return latest, missing_logs

    logs = get_range(latest.date, dt)
    balance = datetime.timedelta(seconds=latest.seconds)
    for day in date_range(latest.date, dt, False):
        work_len = datetime.timedelta(0)
        if logs and logs[0].date == day:
            day_log = logs.pop(0)
            if day_log.is_flex:
                # assume flexed holiday/weekend is a mistake, but show a warning
                if not is_workday(day) and not config.work_weekend:
                    logging.warning(
                        f"Check timesheet on {day}: marked as flex, but is a weekend or holiday"
                    )
                    continue
            elif day_log.clock_in and day_log.clock_out:
                work_len = time_difference(day_log.clock_in, day_log.clock_out, True, config)
        elif not is_workday(day):
            # no log, not a workday
            continue
        else:
            # it's a work day, but no timesheet entry found. ignored by balance calcs.
            # should be explicitly flexed or have logs added
            logging.info(f"{day} missing timesheet data, skipping")
            missing_logs.append(day)
            continue

        if is_workday(day):
            need_len = config.day_length
        else:
            need_len = datetime.timedelta(0)

        net = work_len - need_len
        # breakpoint()
        logging.debug(f"{day}: work_len={work_len} need_len={need_len} net={net}")
        logging.debug(f"old balance: {balance} new balance: {balance + net}")
        balance += net
    if missing_logs:
        logging.warning(
            f"Found {len(missing_logs)} days with missing data: {', '.join([str(d) for d in missing_logs])}"
        )
        logging.warning(f"FlexBalance may be inaccurate")
    return FlexBalance.from_timedelta(dt, balance), missing_logs


@ensure_db(db)
def set_flex_balance(
    dt: datetime.date, bal_dt: datetime.timedelta = None, force: bool = False
) -> FlexBalance:
    existing: Optional[FlexBalance] = (
        db.session.query(FlexBalance).filter(FlexBalance.date == dt).first()
    )
    if existing and force is False:
        if not get_resp(f"Overwrite existing flex balance of {existing.hours} on {existing.date}?"):
            exit(1)

    if bal_dt is None:
        bal, missing_days = get_flex_balance(dt)
        if missing_days:
            missing_str = ", ".join([str(d) for d in missing_days])
            raise NoData(db.db_file, missing_str)
    else:
        bal = FlexBalance(date=dt, seconds=bal_dt.seconds)

    db.session.add(bal)
    db.try_commit(True)
    return bal


@ensure_db(db)
def pto_date(dt: datetime.date, pto_val: bool = True) -> Timesheet:
    day = get_day(dt)
    if day:
        if pto_val == day.is_pto:
            logging.info(f"{dt} already has is_pto={pto_val}")
            return day
        elif pto_val:
            logging.warning(f"Existing work log data on {dt} will be ignored")
    else:
        day = Timesheet(date=dt)
    day.is_pto = pto_val  # type: ignore
    db.session.add(day)
    db.try_commit(True)
    logging.info(f"Marked {dt} is_pto={pto_val}")
    return day


### internal stuff


def merge_times(
    current: Timesheet,
    new_times: Tuple[Optional[datetime.time], Optional[datetime.time]],
    validate: bool = False,
    overwrite: bool = False,
) -> Optional[Timesheet]:
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
                logging.info(f"Skipping {current.date}")
                return
        else:
            # skip any existing values unless overwrite enabled
            skip = []
            if new_times[0] and current.clock_in and not overwrite:
                skip.append(LogType.IN)
            if new_times[1] and current.clock_out and not overwrite:
                skip.append(LogType.OUT)

            if len(skip) == 2:
                # "new" times match or won't overwrite existing values
                return
            elif len(skip) == 1:
                # remove the one that got skipped
                new_times = (
                    new_times[0] if LogType.IN not in skip else None,
                    new_times[1] if LogType.OUT not in skip else None,
                )
            # else leave new_times as is: two new values to update (unlikely unless overwrite)
    else:
        if validate and not get_resp(
            f"Create new entry on {current.date}: clock in {current.clock_in}, clock out {current.clock_out}"
        ):
            logging.info(f"Skipping {current.date}")
            return

    if any(new_times):
        if new_times[0]:
            current.clock_in = new_times[0]  # type: ignore
        if new_times[1]:
            current.clock_out = new_times[1]  # type: ignore
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
    day: datetime.date = None,
    log_in: bool = True,
    log_out: bool = False,
) -> dict[datetime.date, dict[LogType, list[datetime.time]]]:
    results: dict[datetime.date, dict[LogType, list[datetime.time]]] = {}

    logging.debug(f"checking {logfile} for day={day} log_in={log_in} log_out={log_out}")
    open_func = open
    if logfile.name.endswith(".gz"):
        open_func = gzip.open
    with open_func(logfile, "rt") as logs:
        for log_line in logs:
            line_dt = log_date(log_line)
            line_day = line_dt.date()
            line_time = line_dt.time()

            # if no day passed, get all activity from file
            if day:
                # break out of files that won't have the day being looked for
                # skip lines that aren't on the day we're looking for
                if line_day > day:
                    break
                elif line_day < day:
                    continue

            if log_in and any([True for login_str in LOGIN_STRS if login_str in log_line]):
                log_type = LogType.IN
            elif log_out and any([True for logout_str in LOGOUT_STRS if logout_str in log_line]):
                log_type = LogType.OUT
            else:
                continue

            if line_day not in results:
                results[line_day] = {LogType.IN: [], LogType.OUT: []}

            results[line_day][log_type].append(clean_time(line_time))

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

        if first_line is None or last_line is None:
            logging.error(f"Malformed authlog {logfile}, skipping")
            continue

        min_date = log_date(first_line).date()
        max_date = log_date(last_line).date()
        log_index.append(AuthLog(logfile, min_date, max_date))
    # start from the oldest logs (auth.log.4.gz)
    return sorted(log_index, key=lambda x: x.min_date)


def is_holiday(day: datetime.date) -> bool:
    return day.weekday() > 4 or db.session.query(Holiday).filter(Holiday.date == day).count() > 0


def is_workday(day: datetime.date) -> bool:
    return not is_holiday(day)


def get_day(day: datetime.date, missing_okay: bool = True) -> Optional[Timesheet]:
    day_log: Optional[Timesheet] = (
        db.session.query(Timesheet).filter(Timesheet.date == day).scalar()
    )
    if day_log is None and not missing_okay:
        raise NoData(db.db_file, f"timesheet.date={day}")
    return day_log


def get_logs(log_dir: Path = Path("/var/log")) -> Iterable[Path]:
    return log_dir.glob("auth.log*")


def get_range(
    from_day: Optional[datetime.date] = None,
    until_day: Optional[datetime.date] = None,
    missing_okay: bool = True,
) -> list[Timesheet]:
    query = db.session.query(Timesheet)
    if from_day and until_day:
        query = query.filter(Timesheet.date >= from_day, Timesheet.date < until_day)
    elif from_day:
        query = query.filter(Timesheet.date >= from_day)
    elif until_day:
        query = query.filter(Timesheet.date < until_day)

    logs = query.all()
    if len(logs) == 0 and not missing_okay:
        raise RuntimeError(f"No timesheet entries found from {from_day} until {until_day}")
    return logs


def row_exists(idx: datetime.date) -> bool:
    return bool(get_day(idx))


def add_row(
    day: datetime.date,
    clock_in: Optional[datetime.time] = None,
    clock_out: Optional[datetime.time] = None,
    is_flex: bool = False,
    is_pto: bool = False,
) -> Timesheet:
    if clock_in is None and clock_out is None:
        raise ValueError("You must specify at least one time to create a new timesheet entry")
    new_row = Timesheet(date=day, clock_in=clock_in, clock_out=clock_out, is_flex=is_flex)
    db.session.add(new_row)
    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        if "UNIQUE constraint failed" in str(e):
            logging.error(f"Cannot create duplicate log entry for {day}")
            exit(1)
        else:
            raise e
    return new_row


def update_row(
    day: datetime.date,
    clock_in: Optional[datetime.time] = None,
    clock_out: Optional[datetime.time] = None,
    overwrite: bool = False,
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
        info_str = ", ".join([f"{k.replace('_', ' ')} ({getattr(row, k)})" for k in bail])
        plural = "s" if len(bail) > 1 else ""
        logging.error(f"Not overwriting existing log{plural} on {day} for {info_str}")
        exit(1)

    db.session.add(row)
    db.try_commit(True)

    return row
