import datetime
from sqlalchemy import Boolean, Column, Date, Time
from typing import List, Dict, Any

from .db import Base as Base
from .util import Log as Log
from .constants import LOG_TYPES


class Timesheet(Base):
    def __init__(
        self,
        date: datetime.date,
        clock_in: datetime.time,
        clock_out: datetime.time,
        is_flex: bool = False,
        *args: List[Any],
        **kwargs: Dict[str, Any]
    ) -> None:
        ...

    def log(self, log_type: LOG_TYPES) -> Log:
        ...
