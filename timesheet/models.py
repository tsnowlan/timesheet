from sqlalchemy import Column, Date, DateTime
from sqlalchemy.ext.declarative import declarative_base

# sqlalchemy shit
Base = declarative_base()


class Timesheet(Base):
    __tablename__ = "timesheet"

    date = Column(Date, primary_key=True)
    clock_in = Column(DateTime)
    clock_out = Column(DateTime)

    def __repr__(self) -> str:
        return f"<Timesheet date={self.date} in={self.clock_in} out={self.clock_out}"

    def __str__(self) -> str:
        return f"{self.date}\t{self.clock_in}\t{self.clock_out}"