import datetime
from pathlib import Path
from typing import (
    Any,
    Callable,
    List,
    Optional,
    Tuple,
    TypeVar,
    Union,
    overload,
    NamedTuple,
)

import click

from .db import DB
from .constants import LOG_TYPES

F = TypeVar("F", bound=Callable[..., Any])


def ensure_db(db: DB) -> Callable[[F], F]:
    ...


def log_date(log_line: str) -> datetime.datetime:
    ...


def target2dt(
    target: str,
) -> Tuple[Optional[datetime.date], Optional[datetime.date]]:
    ...


def str_in_list(str_list: List[str], norm: Optional[str]) -> Callable[..., str]:
    ...


def validate_datetime(
    ctx: click.Context,
    param: Union[click.Option, click.Argument],
    dt: datetime.datetime,
) -> datetime.datetime:
    ...


@overload
def clean_time(dt_obj: datetime.datetime) -> datetime.datetime:
    ...


@overload
def clean_time(dt_obj: datetime.time) -> datetime.time:
    ...


def round_time(dt_obj: datetime.time) -> datetime.time:
    ...


class AuthLog(NamedTuple):
    file: Path
    min_date: datetime.date
    max_date: datetime.date


class Log(NamedTuple):
    day: datetime.date
    type: LOG_TYPES
    time: datetime.time
