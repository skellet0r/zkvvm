import collections
import functools
import os
import pathlib
import platform
from typing import Optional, Set

import requests
from appdirs import user_cache_dir
from semantic_version import Version


class PlatformError(Exception):
    ...


class VersionManager:
    """zkVyper Version Manager.

    :param str cache_dir: The user-specific cache directory.
    """

    _AMD64 = ("amd64", "x86_64", "i386", "i586", "i686")
    _ARM64 = ("aarch64_be", "aarch64", "armv8b", "armv8l")
    _DEFAULT_CONFIG = {"ZKVVM_CACHE_DIR": user_cache_dir(__name__)}
    _REMOTE_BASE_URL = "https://api.github.com/repos/matter-labs/zkvyper-bin/contents/"

    def __init__(self, cache_dir: Optional[str] = None) -> None:
        config = collections.ChainMap(os.environ, self._DEFAULT_CONFIG)  # type: ignore

        self._config = config.new_child()
        self._session = requests.Session()

        if cache_dir:
            self.cache_dir = pathlib.Path(cache_dir).expanduser().as_posix()

        pathlib.Path(self.cache_dir).mkdir(parents=True, exist_ok=True)

    @functools.cached_property
    def remote_versions(self) -> Set[Version]:
        """Remote zkVyper binary versions compatible with the host system."""
        resp = self._session.get(self._REMOTE_BASE_URL + self._platform_id)
        resp.raise_for_status()

        filenames = [file["name"] for file in resp.json() if file["type"] == "file"]
        return {Version(filename.split("-")[-1][1:]) for filename in filenames}

    @property
    def cache_dir(self) -> str:
        """Cache directory."""
        return self._config["ZKVVM_CACHE_DIR"]

    @cache_dir.setter
    def cache_dir(self, value: str) -> None:
        self._config["ZKVVM_CACHE_DIR"] = value

    @functools.cached_property
    def _platform_id(self) -> str:
        """Platform identifier.

        See `Stack Overflow <https://stackoverflow.com/a/45125525>`_.
        """
        system, machine = platform.system(), platform.machine()
        if system == "Linux" and machine in self._AMD64:
            return "linux-amd64"
        elif system == "Darwin" and machine in self._AMD64:
            return "macosx-amd64"
        elif system == "Darwin" and machine in self._AMD64:
            return "macosx-arm64"
        raise PlatformError()
