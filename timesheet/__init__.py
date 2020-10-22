from timesheet.legacy_timesheet import time_delta
import click
import datetime
import sys

from sqlalchemy.engine import create_engine
from sqlalchemy.orm.session import sessionmaker

from .util import validate_action, validate_datetime
from .constants import *
from .app import db, get_day, get_range, add_log, edit_log, guess_day


@click.command(help="clock in and out")
@click.argument("log_type", metavar="< in | out >", callback=validate_action)
@click.argument(
    "log_time",
    metavar="[TIME_STRING]",
    default=datetime.datetime.now(),
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
def clock(log_type, log_time, guess, db_file):
    db.connect(db_file)
    if guess and log_type == "in":
        new_log = guess_day(log_time.date())
    else:
        new_log = add_log(log_type, log_time.date(), log_time.time())
    print(f"Successfully clocked {log_type} on {new_log.day} at {new_log.time}")


@click.group(help="print out timesheet entries")
@click.pass_context
def print_logs(ctx):
    raise NotImplemented()


@click.group(help="edit an existing log or logs")
@click.pass_context
def edit_logs(ctx):
    raise NotImplemented()


@click.group(help="backfill timesheet logs from system logs")
@click.option(
    "-s",
    "--start-date",
    "start",
    metavar="DATE",
    type=click.DateTime(),
    required=True,
    help="starting date to backfill",
)
@click.option(
    "-e",
    "--end-date",
    "end",
    metavar="DATE",
    type=click.DateTime(),
    help="non-inclusive end date for backfill, defaults to start + 1day",
)
@click.pass_context
def backfill(ctx, start, end):
    raise NotImplemented()


def foo_cb(ctx, param, val):
    print(f"in {param} with val {val} ({type(val)})")
    breakpoint()
    sys.exit()


@click.group()
@click.option(
    "-d",
    "--db-file",
    type=click.Path(dir_okay=False, writable=True),
    default=DEF_DBFILE,
)
@click.option("-v", "--verbose", is_flag=True)
@click.option("--debug", is_flag=True)
@click.option(
    "--foo",
    type=click.DateTime(DATETIME_FORMATS),
    callback=validate_datetime,
)
@click.pass_context
def run_cli(ctx, db_file, verbose, debug, foo):
    ctx.ensure_object(dict)
    print(f"foo: {foo}")
    sys.exit()

    if debug and not verbose:
        verbose = True
    ctx.obj["verbose"] = verbose
    ctx.obj["debug"] = debug
    db.connect(db_file)


####

run_cli.add_command(clock)
run_cli.add_command(print_logs, "print")
run_cli.add_command(edit_logs)
run_cli.add_command(backfill)


def main():
    run_cli()