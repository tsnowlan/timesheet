from pathlib import Path
from typing import Optional, Union

from sqlalchemy import MetaData, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.declarative.api import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

md: MetaData = MetaData()
Base = declarative_base()
Base.metadata = md


class DB(object):
    engine: Engine
    session: scoped_session
    db_file: Path
    metadata: MetaData = md

    def __init__(self, db_file: Optional[Path] = None, echo_sql=False) -> None:
        if db_file:
            self.db_file = db_file
            self._init_session(echo_sql)

    def _init_session(self, echo_sql: bool) -> None:
        db_str = f"sqlite:///{self.db_file}"
        self.engine = create_engine(db_str, echo=echo_sql)
        self.sessionmaker = sessionmaker(bind=self.engine)
        self.session = scoped_session(self.sessionmaker)

    def _validate_conn(self) -> None:
        conn_attrs = ["session", "engine", "db_file"]
        if any([hasattr(self, "session"), hasattr(self, "engine")]):
            assert all(
                [getattr(self, aname, None) for aname in conn_attrs]
            ), f"Malformed DB object: {', '.join([f'self.{x}={getattr(self, x)}' for x in conn_attrs])}"
            assert (
                self.engine_file == self.db_file
            ), f"Active database file {self.engine_file} does not match db_file {self.db_file}"
            assert self.session.is_active, "Dead session"  # type: ignore

    @property
    def engine_file(self) -> Union[Path, None]:
        if getattr(self, "engine", None):
            return Path(make_url(self.engine.url).database)
        return None

    def connect(self, db_file: Optional[Path] = None, echo_sql: bool = False) -> None:
        # no db_file, no connection
        if not any([db_file, hasattr(self, "db_file")]):
            raise ValueError("You must specify db_file on creation or when connecting")

        # ensure any existing connection isn't wonky
        self._validate_conn()

        # don't clobber existing connections / settings
        if all([db_file, hasattr(self, "db_file")]):
            if (self.db_file and db_file != self.db_file) or (self.engine_file and 5):
                raise ValueError("Cannot overwrite existing db_file, create a new DB object")
        elif getattr(self, "session", None):
            # use existing session, maybe give a warning?
            return
        elif db_file:
            self.db_file = db_file

        assert self.db_file, f"self.db_file still unset: received db_file={db_file}"
        self._init_session(echo_sql)

    def create_db(self) -> None:
        Base.metadata.create_all(self.engine)

    def disconnect(self) -> None:
        if hasattr(self, "session"):
            self.session.close()

    def _ensure_db(self) -> None:
        assert (
            getattr(self, "session", None) is not None and getattr(self, "engine", None) is not None
        )
        if not all([self.engine.has_table(t.name) for t in md.sorted_tables]):
            self.create_db()
