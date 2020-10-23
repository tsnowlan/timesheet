import datetime

import click

from .app import add_log, db, edit_log, guess_day, print_all, print_day, print_range
from .constants import DATETIME_FORMATS, DEF_DBFILE, TODAY, VALID_TARGETS
from .util import target2dt, validate_action, validate_datetime, validate_target


@click.command(help="clock in and out")
@click.argument("log_type", metavar="< in | out >", callback=validate_action)
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
    callback=validate_target,
    help=f"time period to print logs from. must be one of: {', '.join(VALID_TARGETS)}",
)
@click.option(
    "--export", is_flag=True, help=f"print in a form easy to paste into the timesheet"
)
@click.pass_context
def print_logs(ctx, target, export):
    format = "export" if export else "print"
    min_date, max_date = target2dt(target)
    if min_date and max_date:
        print_range(min_date, max_date)
    elif min_date:
        print_day(min_date)
    else:
        print_all()


@click.group(help="edit an existing log or logs")
@click.argument(
    "log_time",
    metavar="[TIME_STRING]",
    default=f"{datetime.datetime.now()}",
    type=click.DateTime(DATETIME_FORMATS),
    callback=validate_datetime,
)
@click.option("-i", "--clock-in", callback=validate_datetime, default=TODAY)
@click.pass_context
def edit_logs(ctx):
    raise NotImplemented()
    new_log = edit_log()


@click.group(help="backfill timesheet logs from system logs")
@click.argument(
    "target",
    metavar="< today | month | $month_name | ... >",
    default="today",
    callback=validate_target,
    help=f"time period to backfill logs from. must be one of: {', '.join(VALID_TARGETS)}",
)
@click.pass_context
def backfill(ctx, target) -> None:
    min_date, max_date = target2dt(target)


@click.group()
@click.option(
    "-d",
    "--db-file",
    type=click.Path(dir_okay=False, writable=True),
    default=DEF_DBFILE,
)
@click.option("-v", "--verbose", is_flag=True)
@click.option("--debug", is_flag=True)
@click.pass_context
def run_cli(ctx, db_file, verbose, debug) -> None:
    ctx.ensure_object(dict)

    if debug and not verbose:
        verbose = True
    ctx.obj["verbose"] = verbose
    ctx.obj["debug"] = debug
    db.connect(db_file, debug)


####

run_cli.add_command(clock)
run_cli.add_command(print_logs, "print")
run_cli.add_command(edit_logs, "edit")
run_cli.add_command(backfill)


def main() -> None:
    run_cli()
