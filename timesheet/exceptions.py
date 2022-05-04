import datetime as DT
from pathlib import Path
from typing import Optional, Tuple, Union

from .models import Timesheet


class NoData(Exception):
    def __init__(self, db_file: Path, target: str, message: Optional[str] = None):
        self.db_file = db_file
        self.target = target
        if message is None:
            message = f"No data found for {self.target}"
        self.message = message

    def __str__(self) -> str:
        return self.message


class ExistingData(Exception):
    def __init__(
        self,
        target: Tuple[Timesheet, str],
        value: Union[DT.time, bool],
        message: Optional[str] = None,
    ):
        self.target = target
        self.new_value = value
        if message is None:
            message = f"Cannot overwrite existing {self.target[1]} data on {self.target[0].date}"
        self.message = message

    def __str__(self) -> str:
        return self.message

    @property
    def old_value(self) -> Union[DT.time, bool]:
        return getattr(*self.target)
