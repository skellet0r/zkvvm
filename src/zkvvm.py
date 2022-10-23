import functools
import platform
from typing import Set

import requests
from semantic_version import Version


class PlatformError(Exception):
    ...


class VersionManager:
    _AMD64 = ("amd64", "x86_64", "i386", "i586", "i686")
    _ARM64 = ("aarch64_be", "aarch64", "armv8b", "armv8l")
    _REMOTE_BASE_URL = "https://api.github.com/repos/matter-labs/zkvyper-bin/contents/"

    def __init__(self) -> None:
        self.session = requests.Session()

    @functools.cached_property
    def remote_versions(self) -> Set[Version]:
        """Remote zkVyper binary versions compatible with the host system."""
        resp = self.session.get(self._REMOTE_BASE_URL + self._platform_id)
        resp.raise_for_status()

        filenames = [file["name"] for file in resp.json() if file["type"] == "file"]
        return {Version(filename.split("-")[-1][1:]) for filename in filenames}

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
