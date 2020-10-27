import datetime
from pathlib import Path

import click

from timesheet.constants import LOG_TYPES


def clock(
    log_type: str,
    log_time: datetime.datetime,
    guess: bool,
    overwrite: bool,
    db_file: Path,
) -> None:
    ...


def print_logs(ctx: click.Context, target: str, export: bool) -> None:
    ...


def edit(ctx: click.Context, log_time: datetime.datetime, log_type: LOG_TYPES) -> None:
    ...


def backfill(ctx: click.Context, target: str, validate: bool, overwrite: bool) -> None:
    ...


def run_cli(ctx: click.Context, db_file: Path, debug: bool) -> None:
    ...


def main() -> None:
    ...
