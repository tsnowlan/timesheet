import datetime
from pathlib import Path
import sys

import click
from sqlalchemy.sql.operators import is_

from .app import (
    add_log,
    backfill_days,
    db,
    edit_log,
    guess_day,
    print_all,
    print_day,
    print_range,
)
from .constants import (
    DATETIME_FORMATS,
    DEF_DBFILE,
    TODAY,
    VALID_LOG_TYPES,
    VALID_TARGETS,
)
from .util import str_in_list, target2dt, validate_datetime


@click.command(help="clock in and out")
@click.argument(
    "log_type", metavar="< in | out >", callback=str_in_list(VALID_LOG_TYPES)
)
@click.argument(
    "log_time",
    metavar="[TIME_STRING]",
    default=f"{datetime.datetime.now()}",
    type=click.DateTime(DATETIME_FORMATS),
    callback=validate_datetime,
)
@click.option("-g", "--guess", is_flag=True, help="Guess login time from auth logs")
@click.option(
    "-d",
    "--db-file",
    type=click.Path(dir_okay=False, writable=True),
    default=DEF_DBFILE,
)
def clock(log_type, log_time, guess, db_file) -> None:
    db.connect(db_file)
    if guess and log_type == "in":
        new_log = guess_day(log_time.date())
    else:
        new_log = add_log(log_type, log_time.date(), log_time.time())
    print(f"Successfully clocked {log_type} on {new_log.day} at {new_log.time}")


@click.command(help="print out timesheet entries for the given date(s)")
@click.argument(
    "target",
    metavar="< today | month | $month_name | ... >",
    default="today",
    callback=str_in_list(VALID_TARGETS),
)
@click.option(
    "--export", is_flag=True, help=f"print in a form easy to paste into the timesheet"
)
@click.pass_context
def print_logs(ctx, target, export):
    print_format = "export" if export else "print"
    min_date, max_date = target2dt(target)
    if min_date and max_date:
        print_range(min_date, max_date, print_format)
    elif min_date:
        print_day(min_date)
    else:
        print_all()


@click.group(help="edit an existing log")
@click.argument(
    "log_time",
    metavar="[TIME_STRING]",
    default=TODAY,
    type=click.DateTime(DATETIME_FORMATS),
    callback=validate_datetime,
)
@click.option(
    "-i", "--clock-in", "log_type", flag_value="in", help="edit the clock in time"
)
@click.option(
    "-o", "--out", "log_type", flag_value="out", help="edit the clock out time"
)
@click.pass_context
def edit(ctx, log_time, log_type):
    new_log = edit_log(log_time.day(), log_type, log_time.time())
    print(f"Updated timesheet entry:\n{new_log}")


@click.group(help="backfill timesheet logs from system logs")
@click.argument(
    "target",
    metavar="< today | month | $month_name | ... >",
    default="today",
    callback=str_in_list(VALID_TARGETS),
)
@click.option(
    "-v",
    "--validate",
    is_flag=True,
    help="Requires user input before creating or modifying timesheet logs",
)
@click.pass_context
def backfill(ctx, target: str, validate: bool) -> None:
    f"""
    Backfills timesheet days in the given period from system logs

    Valid arguments: {', '.join(VALID_TARGETS)}
    """
    min_date, max_date = target2dt(target)
    if min_date and not max_date:
        max_date = min_date = datetime.timedelta(days=1)
    elif not min_date and not max_date and ctx.obj["debug"]:
        print(f"Backfilling as far as the logs will let us...", sys.stderr)
    new_logs = backfill_days(min_date, max_date, any(validate, ctx.obj["debug"]))
    if new_logs:
        print(f"Created or updated {len(new_logs)} timesheet entries:")
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
    default=DEF_DBFILE,
)
@click.option("--debug", is_flag=True)
@click.pass_context
def run_cli(ctx, db_file: Path, debug: bool) -> None:
    ctx.ensure_object(dict)
    ctx.obj["debug"] = debug
    db.connect(db_file, debug)


####

run_cli.add_command(clock)
run_cli.add_command(print_logs, "print")
run_cli.add_command(edit)
run_cli.add_command(backfill)


def main() -> None:
    run_cli(obj={})
