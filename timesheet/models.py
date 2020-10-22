from sqlalchemy import Column, Date, Time, Boolean

from .db import Base
from .util import Log


class Timesheet(Base):
    __tablename__ = "timesheet"

    date = Column(Date, primary_key=True, unique=True, index=True)
    clock_in = Column(Time)
    clock_out = Column(Time)
    is_flex = Column(Boolean, default=False)

    def __repr__(self) -> str:
        return f"<Timesheet date={self.date} clock_in={self.clock_in} clock_out={self.clock_out}"

    def __str__(self) -> str:
        return f"{self.date}\t{self.clock_in}\t{self.clock_out}"

    def log(self, log_type):
        return Log(self.date, log_type, getattr(self, f"clock_{log_type}", None))
