import datetime
from typing import TYPE_CHECKING, Literal, Union

from sqlalchemy import Boolean, Column, Date, MetaData, String, Time

if TYPE_CHECKING:
    # sqlalchemy-stubs doesn't support 1.4+, but sqlalchemy2-stubs is still missing a lot
    # so use old stubs for typing hints, and actual import when running
    from sqlalchemy.ext.declarative.api import declarative_base  # type: ignore
else:
    # where declarative_base is actually located now
    from sqlalchemy.orm import declarative_base

from sqlalchemy.sql.sqltypes import Integer

from .enums import LogType
from .util import Log

md: MetaData = MetaData()
Base = declarative_base()
Base.metadata = md


class Timesheet(Base):
    __tablename__ = "timesheet"

    date = Column(Date, primary_key=True, unique=True, index=True)
    clock_in = Column(Time, nullable=True)
    clock_out = Column(Time, nullable=True)
    is_flex = Column(Boolean, default=False)
    is_pto = Column(Boolean, default=False)

    def __repr__(self) -> str:
        return f"<Timesheet date={self.date} clock_in={self.clock_in} clock_out={self.clock_out} flex={self.is_flex}>"

    def __str__(self) -> str:
        if self.is_flex:
            times = ["flexed", "flexed"]
        else:
            times = [self.clock_in, self.clock_out]
        ts_str = f"{self.date}\t{str(times[0]): <8}\t{str(times[1]): <8}"
        return ts_str

    def log(self, log_type: LogType) -> Log:
        log_val: Union[datetime.time, Literal["Af", "Am"], None]
        if self.is_flex:
            log_val = "Af"
        elif self.is_pto:
            log_val = "Am"
        else:
            log_val = getattr(self, log_type.value, None)
        return Log(self.date, log_type, log_val)


class Holiday(Base):
    __tablename__ = "holidays"

    date = Column(Date, primary_key=True, index=True)
    name = Column(String)
    comment = Column(String)


class FlexBalance(Base):
    """
    keeps track of current flextime balance

    balance is tracked in seconds for cleaner math, but hours are used for human readability
    """

    __tablename__ = "flexbalance"

    date = Column(Date, primary_key=True, unique=True, index=True)
    seconds = Column(Integer, nullable=False)

    def __str__(self) -> str:
        return f"{self.date}: {self.hours}h"

    def __repr__(self) -> str:
        return f"<FlexBalance date={self.date} seconds={self.seconds}>"

    @property
    def hours(self) -> float:
        return self.seconds / 3600

    @property
    def hr_min(self) -> str:
        hr, sec = divmod(self.seconds, 3600)
        mins = sec // 60
        return f"{hr}:{mins:02d}"

    @classmethod
    def from_timedelta(cls, dt: datetime.date, bal_dt: datetime.timedelta) -> "FlexBalance":
        secs = bal_dt.seconds + bal_dt.days * 86400
        return cls(date=dt, seconds=secs)
