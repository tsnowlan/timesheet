from collections import defaultdict
import datetime
from pathlib import Path
from typing import List, Literal, Optional, Dict, DefaultDict, Union, overload

from .constants import LOG_TYPES
from .models import Timesheet
from .util import (
    Log as Log,
    AuthLog as AuthLog,
)


def print_day(day: datetime.datetime) -> None:
    ...


def print_range(
    from_day: datetime.date, until_day: datetime.date, print_format: str = "print"
) -> None:
    ...


def print_all() -> None:
    ...


def add_log(
    log_day: datetime.date, log_type: LOG_TYPES, log_time: datetime.time
) -> Log:
    ...


def edit_log(
    log_day: datetime.date, log_type: LOG_TYPES, log_time: datetime.time
) -> Log:
    ...


def guess_day(
    day: datetime.date,
    clock_in: bool = True,
    clock_out: bool = False,
    overwrite: bool = False,
) -> Log:
    ...


def backfill_days(
    from_day: Optional[datetime.date] = None,
    until_day: Optional[datetime.date] = None,
    validate: bool = False,
    overwrite: bool = False,
) -> List[Timesheet]:
    ...


### internal stuff


def merge_times(
    current: Timesheet,
    new_times: tuple[int, int],
    validate: bool = False,
    overwrite: bool = False,
) -> Timesheet:
    ...


def get_resp(msg: str) -> bool:
    ...


def get_activity(
    logfile: Path,
    day: Optional[datetime.date] = None,
    log_in: bool = True,
    log_out: bool = False,
) -> DefaultDict[datetime.date, Dict[LOG_TYPES, List[datetime.datetime]]]:
    ...


def index_logs() -> List[AuthLog]:
    ...


@overload
def get_day(day: datetime.date, missing_okay: Literal[False]) -> Timesheet:
    ...


@overload
def get_day(day: datetime.date, missing_okay: bool = True) -> Optional[Timesheet]:
    ...


def get_logs(log_dir: Path = Path("/var/log")) -> List[Path]:
    ...


def get_range(
    from_day: datetime.date, until_day: datetime.date, missing_okay: bool = True
) -> List[Timesheet]:
    ...


def row_exists(idx: datetime.date) -> bool:
    ...


def add_row(
    day: datetime.date,
    clock_in: Optional[datetime.time] = None,
    clock_out: Optional[datetime.time] = None,
    is_flex: Optional[bool] = False,
) -> Timesheet:
    ...


def update_row(
    day: datetime.date,
    clock_in: Optional[datetime.time] = None,
    clock_out: Optional[datetime.time] = None,
    overwrite: bool = False,
) -> Timesheet:
    ...
