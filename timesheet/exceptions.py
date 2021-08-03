import datetime
from pathlib import Path
from typing import Union, TypeVar

from .models import Base, Timesheet

T = TypeVar("T")


class NoData(Exception):
    def __init__(self, db_file: Path, target: str, message: str = None) -> None:
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
        model: str,
        fieldname: str,
        old_value: T,
        new_value: T,
        message: str = None,
    ) -> None:
        self.model = model
        self.fieldname = fieldname
        self.old_value = old_value
        self.new_value = new_value
        if message is None:
            message = (
                f"Cannot overwrite existing {self.model}.{self.fieldname} = "
                f"{self.old_value} with new value {self.new_value}"
            )
        self.message = message

    def __str__(self) -> str:
        return self.message
