from pathlib import Path
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session

md = MetaData()
Base = declarative_base()
Base.metadata = md


class DB(object):
    engine = None
    session = None
    db_file = None
    metadata = md

    def __init__(self, db_file: Path = None) -> None:
        if db_file:
            self.db_file = db_file
            self._init_session()

    def _init_session(self, echo_sql: bool) -> None:
        db_str = f"sqlite:///{self.db_file}"
        self.engine = create_engine(db_str, echo=echo_sql)
        self.sessionmaker = sessionmaker(bind=self.engine)
        self.session = scoped_session(self.sessionmaker)

    def connect(self, db_file: str = None, echo_sql: bool = False) -> None:
        if db_file is None and self.session is None:
            raise ValueError("You must specify a db_file")
        elif db_file and self.session is None:
            self.db_file = db_file
            self._init_session(echo_sql)

    def create_db(self) -> None:
        Base.metadata.create_all(self.engine)

    def disconnect(self):
        if self.session:
            self.session.close()
        if self.engine:
            self.engine.close()

    def ensure_db(self) -> None:
        if not all([self.engine.has_table(t.name) for t in md.sorted_tables]):
            self.create_db()
