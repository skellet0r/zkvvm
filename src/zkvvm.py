import argparse
import collections
import functools
import logging
import os
import pathlib
import platform
import urllib.parse
from typing import Any, FrozenSet

import requests
import tqdm
from appdirs import user_cache_dir, user_log_dir
from semantic_version import Version

logger = logging.getLogger(__name__)


class PlatformError(Exception):
    ...


class Config(collections.UserDict):
    """Configuration container with attribute access support."""

    DEFAULTS = {
        "cache_dir": pathlib.Path(user_cache_dir(__name__)),
        "log_file": pathlib.Path(user_log_dir(__name__)).joinpath(__name__ + ".log"),
        "verbosity": logging.ERROR,
    }
    CONVERTERS = {
        "cache_dir": lambda x: pathlib.Path(x).absolute(),
        "log_file": lambda x: pathlib.Path(x).absolute(),
        "verbosity": int,
    }

    def __init__(self, **kwargs: Any) -> None:
        env, prefix = {}, __name__ + "_"
        for k, v in os.environ.items():
            if not k.startswith(prefix.upper()):
                continue
            key = k.lower()[len(prefix) :]
            env[key] = self.CONVERTERS[key](v)  # type: ignore

        user = {
            k: self.CONVERTERS[k](v)  # type: ignore
            for k, v in kwargs.items()
            if v is not None
        }
        self.data = collections.ChainMap(user, env, self.DEFAULTS)  # type: ignore


class BinaryVersion(Version):
    def __init__(self, *args, location: str, **kwargs):
        super().__init__(*args, **kwargs)
        self.location = location


class VersionManager:
    """zkVyper Version Manager."""

    _AMD64 = ("amd64", "x86_64", "i386", "i586", "i686")
    _ARM64 = ("aarch64_be", "aarch64", "armv8b", "armv8l")
    _REMOTE_BASE_URL = "https://api.github.com/repos/matter-labs/zkvyper-bin/contents/"

    def __init__(self, config: Config) -> None:
        self._session = requests.Session()
        self._config = config

        log_file: pathlib.Path = config["log_file"]
        if not log_file.exists():
            log_file.parent.mkdir(parents=True)

        self._logger = self._get_logger()

    def install(self, version: BinaryVersion, overwrite: bool = False):
        if version in self.local_versions and not overwrite:
            return
        show_progress = self._config["verbosity"] <= logging.INFO

        self._logger.info(f"Installing zkVyper v{version!s} from {version.location!r}.")
        resp = self._session.get(version.location, stream=show_progress)

        fp: pathlib.Path = self._config["cache_dir"] / ("zkvyper-" + str(version))
        f = fp.open("wb")
        try:
            if show_progress:
                with tqdm.tqdm(
                    total=int(resp.headers["content-length"]), unit="b", unit_scale=True
                ) as prog:
                    for chunk in resp.iter_content():
                        f.write(chunk)
                        prog.update(len(chunk))
            else:
                f.write(resp.content)
        except BaseException as exc:
            f.close()
            fp.unlink()
            self._logger.error(f"Installation of v{version!s} failed.")
            self._logger.debug("", exc_info=exc)
            raise
        else:
            f.close()
            self._logger.info(f"Installation of v{version!s} finished.")

    def uninstall(self, version: BinaryVersion):
        try:
            pathlib.Path(urllib.parse.urlparse(version.location).path).unlink()
        except FileNotFoundError:
            self._logger.warning(
                f"zkVyper v{version!s} not found at {version.location!r}."
            )
        else:
            self._logger.info(
                f"Uninstalling zkVyper v{version!s} found at {version.location!r}."
            )

    @functools.cached_property
    def remote_versions(self) -> FrozenSet[BinaryVersion]:
        """Remote zkVyper binary versions compatible with the host system."""
        remote_url = self._REMOTE_BASE_URL + self._platform_id
        self._logger.debug(f"Fetching remote zkVyper versions from {remote_url!r}.")
        resp = self._session.get(remote_url)
        resp.raise_for_status()

        versions = set()
        for file in resp.json():
            if file["type"] != "file":
                continue
            version_string = file["name"].split("-")[-1][1:]
            versions.add(BinaryVersion(version_string, location=file["download_url"]))
        self._logger.debug(f"Found {len(versions)} zkVyper versions.")
        return frozenset(versions)

    @property
    def local_versions(self) -> FrozenSet[BinaryVersion]:
        """Local zkVyper binary versions."""
        versions = set()
        cache_dir: pathlib.Path = self._config["cache_dir"]
        for fp in cache_dir.iterdir():
            if not fp.is_file():
                continue
            versions.add(BinaryVersion(fp.name.split("-")[-1], location=fp.as_uri()))
        return frozenset(versions)

    def _get_logger(self):
        _logger = logger.getChild(self.__class__.__name__)
        _logger.setLevel(logging.DEBUG)

        if not _logger.hasHandlers():
            fh = logging.FileHandler(self._config["log_file"])
            fh.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))
            _logger.addHandler(fh)

            ch = logging.StreamHandler()
            ch.setLevel(self._config["verbosity"])
            _logger.addHandler(ch)

        return _logger

    @functools.cached_property
    def _platform_id(self) -> str:
        """Platform identifier.

        See `Stack Overflow <https://stackoverflow.com/a/45125525>`_.
        """
        system, machine = platform.system(), platform.machine().lower()
        if system == "Linux" and machine in self._AMD64:
            return "linux-amd64"
        elif system == "Darwin" and machine in self._AMD64:
            return "macosx-amd64"
        elif system == "Darwin" and machine in self._AMD64:
            return "macosx-arm64"
        raise PlatformError()


def main():
    # top-level parser
    parser = argparse.ArgumentParser("zkvvm", description="zkVyper Version Manager")
    subparsers = parser.add_subparsers(title="commands", dest="command")

    subparsers.add_parser("ls-remote", help="List available remote versions")
    args = parser.parse_args()

    vm = VersionManager(Config())
    if args.command == "ls-remote":
        print(*map(str, vm.remote_versions), sep="\n")


if __name__ == "__main__":
    main()
