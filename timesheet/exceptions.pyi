import datetime
import datetime
from .models import Timesheet
from typing import Optional, Tuple, Union
from pathlib import Path


class NoData(Exception):
    db_file: Path
    target: datetime.date
    message: str

    def __init__(
        self, db_file: Path, target: datetime.date, message: Optional[str] = None
    ) -> None:
        ...


class ExistingData(Exception):
    target: Tuple[Timesheet, str]
    value: Union[datetime.time, bool]
    messsage: str

    def __init__(
        self,
        target: Tuple[Timesheet, str],
        value: Union[datetime.time, bool],
        message: Optional[str] = None,
    ) -> None:
        ...

    @property
    def old_value(self) -> Union[datetime.time, bool]:
        ...
