import collections
import functools
import os
import pathlib
import platform
from typing import Any, Set

import requests
from appdirs import user_cache_dir, user_log_dir
from semantic_version import Version


class PlatformError(Exception):
    ...


class Config(collections.UserDict):
    """Configuration container with attribute access support."""

    DEFAULTS = {
        "cache_dir": pathlib.Path(user_cache_dir(__name__)),
        "log_file": pathlib.Path(user_log_dir(__name__)).joinpath(__name__ + ".log"),
    }

    def __init__(self, **kwargs: Any) -> None:
        env, prefix = {}, __name__ + "_"
        for k, v in os.environ.items():
            if not k.startswith(prefix.upper()):
                continue
            key = k.lower()[len(prefix) :]
            env[key] = type(self.DEFAULTS[key])(v)

        user = {k: type(self.DEFAULTS[k])(v) for k, v in kwargs.items()}
        self.data = collections.ChainMap(user, env, self.DEFAULTS)  # type: ignore

    def __getattr__(self, name: str) -> Any:
        try:
            return self.data[name]
        except KeyError:
            raise AttributeError()

    def __setattr__(self, name: str, value: Any) -> None:
        self.data[name] = value


class VersionManager:
    """zkVyper Version Manager."""

    _AMD64 = ("amd64", "x86_64", "i386", "i586", "i686")
    _ARM64 = ("aarch64_be", "aarch64", "armv8b", "armv8l")
    _REMOTE_BASE_URL = "https://api.github.com/repos/matter-labs/zkvyper-bin/contents/"

    def __init__(self, config: Config) -> None:
        self._session = requests.Session()
        self._config = config

    @functools.cached_property
    def remote_versions(self) -> Set[Version]:
        """Remote zkVyper binary versions compatible with the host system."""
        resp = self._session.get(self._REMOTE_BASE_URL + self._platform_id)
        resp.raise_for_status()

        filenames = [file["name"] for file in resp.json() if file["type"] == "file"]
        return {Version(filename.split("-")[-1][1:]) for filename in filenames}

    @property
    def local_versions(self) -> Set[Version]:
        """Local zkVyper binary versions."""
        versions = set()
        for fp in self._config.cache_dir.iterdir():
            if not fp.is_file():
                continue
            versions.add(Version(fp.name.split("-")[-1]))
        return versions

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
