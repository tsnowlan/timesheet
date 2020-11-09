import datetime
import sys
from pathlib import Path
from typing import Optional

import click

from .app import (
    add_log,
    backfill_days,
    config as app_config,
    db,
    edit_log,
    guess_day,
    print_range,
)
from .constants import DATETIME_FORMATS, ROW_HEADER, TODAY
from .enums import AllTargets, AllTargetsType, LogType
from .exceptions import ExistingData, NoData
from .util import str2enum, target2dt, validate_datetime


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
    default=f"{datetime.datetime.now()}",
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
    update_config(config_file, db_file)
    db.connect(app_config.db_file, app_config.debug)

    try:
        if guess:
            guess_args = [log_type == lt for lt in LogType] + [overwrite]
            new_log = guess_day(log_time.date(), *guess_args).log(log_type)
        else:
            new_log = add_log(log_time.date(), log_type, log_time.time())
    except (ExistingData, NoData) as e:
        print(e)
        sys.exit(1)
    print(f"Successfully clocked {log_type.name.lower()} on {new_log.day} at {new_log.time}")


@click.command(help="print out timesheet entries for the given date(s)")
@click.argument(
    "target",
    metavar="< today | month | $month_name | ... >",
    default="today",
    callback=str2enum,
)
@click.option("--export", is_flag=True, help=f"print in a form easy to paste into the timesheet")
def print_logs(target: AllTargetsType, export: bool) -> None:
    print_format = "export" if export else "print"
    min_date, max_date = target2dt(target)
    try:
        print_range(min_date, max_date, print_format)
    except NoData as e:
        print(e)
        sys.exit(1)


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
        print(e)
        sys.exit(1)
    print(f"Updated timesheet entry:\n{ROW_HEADER}")
    print(new_log)


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
        print(f"Backfilling as far as the logs will let us...", file=sys.stderr)
    new_logs = backfill_days(
        min_date, max_date, use_standard, any([validate, app_config.debug]), overwrite
    )
    if new_logs:
        print(f"Created or updated {len(new_logs)} timesheet entries:")
        print(ROW_HEADER)
        for log in new_logs:
            print(log)
    else:
        print(f"No timesheet entries changed")
        sys.exit(1)


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
@click.option("--debug", is_flag=True)
def run_cli(
    db_file: Optional[Path],
    config_file: Optional[Path],
    debug: bool,
) -> None:
    update_config(config_file, db_file, debug)
    db.connect(app_config.db_file, app_config.debug)


def update_config(
    config_file: Optional[Path] = None,
    db_file: Optional[Path] = None,
    debug: bool = False,
) -> None:
    """ Updates config from cli options """
    if config_file:
        app_config.from_file(config_file)
    if db_file and db_file != app_config.db_file:
        app_config.db_file = db_file
    if debug:
        app_config.debug = debug


####

run_cli.add_command(clock)
run_cli.add_command(print_logs, "print")
run_cli.add_command(edit)
run_cli.add_command(backfill)


def main() -> None:
    run_cli(obj={})
