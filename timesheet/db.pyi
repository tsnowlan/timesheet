from pathlib import Path
from typing import Optional, Type, Union

from sqlalchemy import MetaData
from sqlalchemy.engine import Engine
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.orm import scoped_session


class Base(DeclarativeMeta):
    ...


class DB(object):
    engine = None  # type: Engine
    session = None  # type: scoped_session
    db_file = None  # type: Path
    metadata: MetaData

    def __init__(self, db_file: Optional[Path] = None, echo_sql=False) -> None:
        ...

    def _init_session(self, echo_sql: bool) -> None:
        ...

    def _validate_conn(self) -> None:
        ...

    @property
    def engine_file(self) -> Union[Path, None]:
        ...

    def connect(self, db_file: Optional[Path] = None, echo_sql: bool = False) -> None:
        ...

    def create_db(self) -> None:
        ...

    def disconnect(self) -> None:
        ...

    def _ensure_db(self) -> None:
        ...
