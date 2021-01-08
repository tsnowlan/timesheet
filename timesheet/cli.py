import datetime
import logging
import sys
from io import TextIOWrapper
from pathlib import Path
from typing import Optional

import click

from .app import (
    config as app_config,
    db,
    add_log,
    backfill_days,
    edit_log,
    flex_date,
    get_flex_balance,
    guess_day,
    import_calendar,
    print_range,
    set_flex_balance,
)
from .constants import DATE_FORMATS, DATETIME_FORMATS, ROW_HEADER, TODAY
from .enums import AllTargets, AllTargetsType, LogType
from .exceptions import ExistingData, NoData
from .util import dt2date, init_logs, str2enum, target2dt, validate_datetime


def init_app(
    config_file: Path = None,
    db_file: Path = None,
    log_level: int = logging.WARNING,
) -> None:
    """ Updates config from cli options """
    if config_file:
        app_config.from_file(config_file)
    if db_file and db_file != app_config.db_file:
        app_config.db_file = db_file
    app_config.debug = log_level == logging.DEBUG
    init_logs(log_level)
    db.connect(app_config.db_file)


###############
# timesheet
###############


@click.group()
@click.option(
    "-d",
    "--db-file",
    type=click.Path(dir_okay=False, writable=True),
)
@click.option(
    "-c",
    "--config-file",
    type=click.Path(dir_okay=False),
    envvar="TIMESHEET_CONFIG",
    help="File with custom config settings",
)
@click.option("--verbose", "log_level", flag_value=logging.INFO, help="Set logging to info")
@click.option("--debug", "log_level", flag_value=logging.DEBUG, help="Set logging to debug")
def run_cli(
    db_file: Optional[Path],
    config_file: Optional[Path],
    log_level: int = logging.WARNING,
) -> None:
    init_app(config_file, db_file, log_level)


###############
# clock
## timesheet clock
###############


@click.command(help="clock in and out")
@click.option(
    "-c",
    "--config-file",
    type=click.Path(dir_okay=False),
    envvar="TIMESHEET_CONFIG",
    hidden=True,
)
@click.argument("log_type", metavar="< in | out >", callback=str2enum)
@click.argument(
    "log_time",
    metavar="[TIME_STRING]",
    default=str(datetime.datetime.now()),
    type=click.DateTime(DATETIME_FORMATS),
    callback=validate_datetime,
)
@click.option("-g", "--guess", is_flag=True, help="Guess login time from auth logs")
@click.option("-f", "--overwrite", is_flag=True, help="overwrite any exisiting entry")
@click.option(
    "-d",
    "--db-file",
    type=click.Path(dir_okay=False, writable=True),
    hidden=True,
)
def clock(
    log_type: LogType,
    log_time: datetime.datetime,
    guess: bool,
    overwrite: bool,
    config_file: Optional[Path],
    db_file: Optional[Path],
) -> None:
    init_app(config_file, db_file)

    try:
        if guess:
            guess_args = [log_type == lt for lt in LogType] + [overwrite]
            new_log = guess_day(log_time.date(), *guess_args).log(log_type)
        else:
            new_log = add_log(log_time.date(), log_type, log_time.time())
    except (ExistingData, NoData) as e:
        logging.error(e)
        exit(1)
    print(f"Successfully clocked {log_type.name.lower()} on {new_log.day} at {new_log.time}")


###############
## timesheet backfill
###############


@click.command(help="backfill timesheet logs from system logs")
@click.argument(
    "target",
    metavar="< today | month | $month_name | ... >",
    default="today",
    callback=str2enum,
)
@click.option("--std", "use_standard", is_flag=True, help="Use standard times if no logs found")
@click.option(
    "-v",
    "--validate",
    is_flag=True,
    help="Requires user input before creating or modifying timesheet logs",
)
@click.option(
    "-f",
    "--overwrite",
    is_flag=True,
    help="overwrite existing entries without prompting",
)
def backfill(target: AllTargetsType, use_standard: bool, validate: bool, overwrite: bool) -> None:
    f"""
    Backfills timesheet days in the given period from system logs

    Valid arguments: {', '.join(AllTargets)}
    """
    min_date, max_date = target2dt(target)
    if min_date and not max_date:
        max_date = min_date + datetime.timedelta(days=1)
    elif not min_date and not max_date:
        logging.debug(f"Backfilling as far as the logs will let us...", file=sys.stderr)
    new_logs = backfill_days(
        min_date, max_date, use_standard, any([validate, app_config.debug]), overwrite
    )
    if new_logs:
        print(f"Created or updated {len(new_logs)} timesheet entries:")
        print(ROW_HEADER)
        for log in new_logs:
            print(log)
    else:
        logging.info(f"No timesheet entries changed")
        exit(1)


###############
## timesheet edit
###############


@click.command(help="edit an existing log")
@click.argument("log_type", metavar="< in | out >", callback=str2enum)
@click.argument(
    "log_time",
    metavar="[TIME_STRING]",
    default=TODAY,
    type=click.DateTime(DATETIME_FORMATS),
    callback=validate_datetime,
)
def edit(log_type: LogType, log_time: datetime.datetime) -> None:
    try:
        new_log = edit_log(log_time.date(), log_type, log_time.time())
    except NoData as e:
        logging.error(e)
        exit(1)
    print(f"Updated timesheet entry:\n{ROW_HEADER}")
    print(new_log)


###############
## timesheet print
###############


@click.command(
    "print",
    short_help="print timesheet entries",
    help="prints out timesheet entries for the given date or range of dates",
)
@click.argument(
    "target",
    metavar="< today | month | $month_name | ... >",
    default="today",
    callback=str2enum,
)
@click.option("--export", is_flag=True, help=f"print in a form easy to paste into the spreadsheet")
def print_logs(target: AllTargetsType, export: bool) -> None:
    print_format = "export" if export else "print"
    min_date, max_date = target2dt(target)
    try:
        print_range(min_date, max_date, print_format)
    except NoData as e:
        logging.error(e)
        exit(1)


###############
## timesheet update-holidays
###############


@click.command(help="updates the holidays table")
@click.argument("cal", metavar="calendar.ics", type=click.File())
def update_holidays(cal: TextIOWrapper):
    """ ics file from e.g., https://www.calendarlabs.com/ical-calendar/holidays/norway-holidays-62/ """
    import_calendar(cal)


###############
## timesheet balance
###############


@click.group(help="view and manage flex balance")
def balance():
    pass


###############
### timesheet balance show
###############


@balance.command("show", help=f"show flex balance for the given date (default: {TODAY})")
@click.argument(
    "date",
    metavar="[DATE]",
    type=click.DateTime(DATE_FORMATS),
    callback=dt2date,
    default=str(TODAY),
)
def get_balance(date: datetime.date):
    try:
        current_balance, _ = get_flex_balance(date)
    except NoData as e:
        print(e)
        exit(1)
    when = "Current" if date == TODAY else str(date)
    print(f"{when} balance: {current_balance.hours}h")


###############
### timesheet balance set
###############


@balance.command("set", help="set flex balance in hours at a given date")
@click.argument(
    "date", metavar="DATE", type=click.DateTime(DATE_FORMATS), callback=dt2date, required=True
)
@click.argument("balance", type=float, required=True)
@click.option("--force", is_flag=True, help="overwrite any existing balance on the given day")
def set_balance(date: datetime.date, balance: float, force: bool):
    balance_dt = datetime.timedelta(hours=balance)
    try:
        new_balance = set_flex_balance(date, balance_dt, force)
    except NoData as e:
        print(e)
        exit(1)
    print(f"New flex balance: {new_balance.hours}h")


###############
### timesheet balance update
###############


@balance.command("update", help="update flex balance table to the current day")
@click.option("--force", is_flag=True, help="overwrite any existing balance for today")
def update_balance():
    try:
        new_balance = set_flex_balance(TODAY)
    except NoData as e:
        print(e)
        exit(1)
    print(f"New flex balance: {new_balance.hours}h")


###############
## timesheet flex
###############


@click.command(
    "flex",
    short_help="mark a day as flexed",
    help=f"mark the given date as flexed (default: {TODAY})",
)
@click.argument(
    "date",
    metavar="[DATE]",
    type=click.DateTime(DATE_FORMATS),
    callback=dt2date,
    default=str(TODAY),
)
@click.option("--unflex", "flex_val", flag_value=False, help="unmark a date as flexed")
@click.option("--flex", "flex_val", flag_value=True, default=True, hidden=True)
def flex_day(date: datetime.date, flex_val: bool):
    new_day = flex_date(date, flex_val)
    print(f"new day:\n{new_day}")


###############

run_cli.add_command(clock)
run_cli.add_command(backfill)
run_cli.add_command(edit)
run_cli.add_command(print_logs)
run_cli.add_command(update_holidays)
run_cli.add_command(balance)
run_cli.add_command(flex_day)
