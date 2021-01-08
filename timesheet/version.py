from typing import Optional, overload
import pkg_resources
from pathlib import Path

vfile = Path(__file__).parent / "VERSION"
file_version = vfile.read_text().strip()
try:
    # show installed package version, if applicable
    pkg_version = pkg_resources.require(__package__)[0].version
    __version__ = pkg_version
except pkg_resources.DistributionNotFound:
    # fallback to file_version
    pkg_version = None
    __version__ = file_version


@overload
def get_version(pretty: bool = True) -> str:
    ...


def get_version(pretty: bool = False) -> tuple[str, str, str, Optional[str]]:
    if pretty is True:
        return f"{__package__} {__version__}"  # type: ignore

    vstr = __version__[1:] if __version__.startswith("v") else __version__
    maj, min, bugfix = vstr.split(".")
    if "." in bugfix:
        bugfix, special = bugfix.split(".", 1)
    else:
        special = None
    return maj, min, bugfix, special
