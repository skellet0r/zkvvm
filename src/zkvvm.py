import collections
import functools
import logging
import os
import pathlib
import platform
from typing import Any, Optional, Set

import requests
from appdirs import user_cache_dir, user_log_dir
from semantic_version import SimpleSpec, Version

logger = logging.getLogger(__name__)


class PlatformError(Exception):
    ...


class Config(collections.UserDict):
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


class Configuration:
    _DEFAULT_CONFIG = {
        "ZKVVM_CACHE_DIR": user_cache_dir(__name__),
        "ZKVVM_LOG_FILE": os.path.join(user_log_dir(__name__), "zkvvm.log"),
        "ZKVVM_ACTIVE_VERSION": ">=1.1.0",
        "ZKVVM_VYPER_VERSION": "^0.3.3",
    }

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        log_file: Optional[str] = None,
        active_version: Optional[str] = None,
        vyper_version: Optional[str] = None,
    ) -> None:
        config = collections.ChainMap(os.environ, self._DEFAULT_CONFIG)  # type: ignore
        self._config = config.new_child()

        self.cache_dir = cache_dir or self.cache_dir
        self.log_file = log_file or self.log_file
        self.active_version = active_version or self.active_version
        self.vyper_version = vyper_version or self.vyper_version

    @property
    def cache_dir(self) -> str:
        """Cache directory."""
        return self._config["ZKVVM_CACHE_DIR"]

    @cache_dir.setter
    def cache_dir(self, value: str) -> None:
        path = pathlib.Path(value).expanduser()
        self._config["ZKVVM_CACHE_DIR"] = path.as_posix()

        if not path.exists():
            path.mkdir(parents=True)

    @property
    def log_file(self) -> str:
        """Log file."""
        return self._config["ZKVVM_LOG_FILE"]

    @log_file.setter
    def log_file(self, value: str) -> None:
        path = pathlib.Path(value).expanduser()
        self._config["ZKVVM_LOG_FILE"] = path.as_posix()

    @property
    def active_version(self) -> str:
        """Active zkVyper version."""
        return self._config["ZKVVM_ACTIVE_VERSION"]

    @active_version.setter
    def active_version(self, value: str) -> None:
        self._config["ZKVVM_ACTIVE_VERSION"] = str(SimpleSpec(value))

    @property
    def vyper_version(self) -> str:
        """Vyper version to use with active zkVyper version."""
        return self._config["ZKVVM_VYPER_VERSION"]

    @vyper_version.setter
    def vyper_version(self, value: str) -> None:
        self._config["ZKVVM_VYPER_VERSION"] = str(SimpleSpec(value))


class VersionManager:
    """zkVyper Version Manager.

    :param str cache_dir: The user-specific cache directory.
    :param str log_file: The runtime log file.
    """

    _AMD64 = ("amd64", "x86_64", "i386", "i586", "i686")
    _ARM64 = ("aarch64_be", "aarch64", "armv8b", "armv8l")
    _REMOTE_BASE_URL = "https://api.github.com/repos/matter-labs/zkvyper-bin/contents/"

    def __init__(self, config: Configuration) -> None:
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
        cache_dir = pathlib.Path(self._config.cache_dir)
        versions = set()
        for fp in cache_dir.iterdir():
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
