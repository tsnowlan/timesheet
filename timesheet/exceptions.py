import datetime
from .models import Timesheet
from typing import Optional, Tuple, Union
from pathlib import Path


class NoData(Exception):
    def __init__(
        self, db_file: Path, target: datetime.date, message: Optional[str] = None
    ) -> None:
        self.db_file = db_file
        self.target = target
        if message is None:
            message = f"No data found on {self.target}"
        self.message = message

    def __str__(self) -> str:
        return self.message


class ExistingData(Exception):
    def __init__(
        self,
        target: Tuple[Timesheet, str],
        value: Union[datetime.time, bool],
        message: Optional[str] = None,
    ) -> None:
        self.target = target
        self.new_value = value
        if message is None:
            message = f"Cannot overwrite existing {self.target[1]} data on {self.target[0].date}"
        self.message = message

    def __str__(self) -> str:
        return self.message

    @property
    def old_value(self) -> Union[datetime.time, bool]:
        return getattr(*self.target)