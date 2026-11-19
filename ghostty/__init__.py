from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("libghostty-py")
except PackageNotFoundError:
    import tomllib
    from pathlib import Path

    with (Path(__file__).resolve().parents[1] / "pyproject.toml").open("rb") as config:
        __version__ = tomllib.load(config)["project"]["version"]

from ._ffi import ffi, lib, GhosttyError
from .core import Terminal, UnknownSequence
