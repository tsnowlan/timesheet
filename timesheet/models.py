from sqlalchemy import Boolean, Column, Date, Time

from .db import Base
from .enums import LogType
from .util import Log


class Timesheet(Base):
    __tablename__ = "timesheet"

    date = Column(Date, primary_key=True, unique=True, index=True)
    clock_in = Column(Time, nullable=True)
    clock_out = Column(Time, nullable=True)
    is_flex = Column(Boolean, default=False)

    def __repr__(self) -> str:
        return f"<Timesheet date={self.date} clock_in={self.clock_in} clock_out={self.clock_out} flex={self.is_flex}>"

    def __str__(self) -> str:
        return f"{self.date}\t{self.clock_in}\t{self.clock_out}"

    def log(self, log_type: LogType) -> Log:
        return Log(self.date, log_type, getattr(self, log_type.value, None))
