import datetime
import logging
from pathlib import Path
from typing import Optional

from .enums import ConfigFormat
from .util import time_difference

DEF_DBFILE = Path().home() / "timesheet.db"


class Config:
    standard_start = datetime.time(9, 0)
    standard_quit = datetime.time(16, 30)
    _day_length: Optional[datetime.timedelta] = None
    work_weekend = False
    round_interval = 15
    round_threshold = round_interval // 2
    db_file = DEF_DBFILE
    debug = False

    def __init__(self, config_file: Optional[Path] = None, **kwargs) -> None:
        if config_file:
            self.from_file(config_file)

        if kwargs:
            self.update(**kwargs)

    @property
    def day_length(self):
        if not self._day_length:
            self._day_length = time_difference(self.standard_quit, self.standard_start)
        return self._day_length

    def from_file(self, config_file: Path, strict: bool = False) -> None:
        if not config_file.exists():
            err = OSError(f"Specified config file {config_file} does not exist")
            if strict:
                raise (err)
            else:
                logging.warning(f"{err}. Continuing with system defaults...")
                return

        try:
            format = ConfigFormat[config_file.suffix]
        except KeyError:
            raise ValueError(
                f"Unrecognized config format {config_file}. Must be one of: "
                + ", ".join([f.value for f in ConfigFormat])
            )

        if format.value == "json":
            self._from_json(config_file)
        elif format.value == "yaml":
            self._from_yaml(config_file)
        else:
            self._from_toml(config_file)

    def update(self, strict: bool = False, **kwargs) -> None:
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)
            else:
                err = KeyError(f"Invalid config option: {k}")
                if strict:
                    raise err
                else:
                    logging.warning(f"{err}. Skipping...")

    def _from_json(self, config_file: Path) -> None:
        import json

        self.update(**json.loads(config_file.read_text()))

    def _from_yaml(self, config_file: Path) -> None:
        try:
            import yaml
        except ModuleNotFoundError:
            logging.error(
                f"Could not import yaml to parse config {config_file}. "
                f"Use a different format or make sure PyYAML is installed correctly"
            )
            exit(1)
        try:
            # Use LibYAML if available
            from yaml import CSafeLoader as SafeLoader
        except ImportError:
            from yaml import SafeLoader  # type: ignore

        self.update(**yaml.load(config_file.read_text(), Loader=SafeLoader))

    def _from_toml(self, config_file: Path) -> None:
        try:
            import toml
        except ModuleNotFoundError:
            logging.error(
                f"Could not load toml to parse config {config_file}. "
                f"Use a different format or make sure toml is installed correctly"
            )
            exit(1)

        self.update(**toml.loads(config_file.read_text()))

    def __iter__(self):
        for k in self.__annotations__:
            yield (k, getattr(self, k))
