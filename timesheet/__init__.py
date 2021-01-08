from pathlib import Path

version_file = Path(__file__).parent / "VERSION"
__version__ = version_file.read_text().strip()
version = __version__
