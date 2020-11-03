import datetime
from pathlib import Path
import sys
from typing import MutableMapping, Optional, Dict, Any, Literal, Tuple

from .constants import VALID_CONFIG_FORMATS, DEF_DBFILE


class Config(object):
    default_start: datetime.time = datetime.time(9, 0)
    default_quit: datetime.time = datetime.time(16, 30)
    round_interval: int = 15
    round_thresholds: Dict[Literal["in", "out"], Tuple[int, int]] = {
        "in": (8, 8),
        "out": (7, 8),
    }
    db_file: Path = DEF_DBFILE
    debug: bool = False

    def __init__(self, config_file: Optional[Path] = None, **kwargs) -> None:
        if config_file:
            self.from_file(config_file)

        if kwargs:
            self.update(**kwargs)

    def from_file(self, config_file: Path, strict: bool = False) -> None:
        if not config_file.exists():
            err = OSError(f"Specified config file {config_file} does not exist")
            if strict:
                raise (err)
            else:
                print(
                    f"WARNING: {err}. Continuing with system defaults...",
                    sys.stderr,
                )
                return

        if config_file.suffix not in VALID_CONFIG_FORMATS:
            raise ValueError(
                f"Unrecognized config format {config_file}. Must be one of: {', '.join(VALID_CONFIG_FORMATS.keys())}"
            )

        if VALID_CONFIG_FORMATS[config_file.suffix] == "json":
            config = self._from_json(config_file)
        elif VALID_CONFIG_FORMATS[config_file.suffix] == "yaml":
            config = self._from_yaml(config_file)
        elif VALID_CONFIG_FORMATS[config_file.suffix] == "toml":
            config = self._from_toml(config_file)
        else:
            raise ValueError(f"Cannot parse config file: {config_file}")

        self.update(**config)

    def update(self, strict: bool = False, **kwargs) -> None:
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)
            else:
                err = KeyError(f"Invalid config option: {k}")
                if strict:
                    raise err
                else:
                    print(f"WARNING: {err}. Skipping...", file=sys.stderr)

    def _from_json(cls, config_file: Path) -> Dict[str, Any]:
        import json

        return json.loads(config_file.read_text())

    def _from_yaml(self, config_file: Path) -> Dict[str, Any]:
        try:
            import yaml
        except ModuleNotFoundError:
            print(
                f"Could not import yaml to parse config f{config_file}. Use a different format or make sure PyYAML is installed correctly"
            )
            sys.exit(1)
        try:
            # Use LibYAML if available
            from yaml import CSafeLoader as SafeLoader
        except ImportError:
            from yaml import SafeLoader  # type: ignore

        return yaml.load(config_file.read_text(), Loader=SafeLoader)

    def _from_toml(self, config_file: Path) -> Dict[str, Any]:
        try:
            import toml
        except ModuleNotFoundError:
            print(
                f"Could not load toml to parse config f{config_file}. Use a different format or make sure toml is installed correctly"
            )
            sys.exit(1)
        return toml.loads(config_file.read_text())  # type: ignore

    def __iter__(self):
        for k in self.__annotations__:
            yield (k, getattr(self, k))
