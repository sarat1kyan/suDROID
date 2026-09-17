"""Locate adb/fastboot/heimdall, download Google platform-tools when missing."""

from __future__ import annotations

import logging
import os
import platform
import shutil
import stat
import sys
import tempfile
import zipfile
from collections.abc import Sequence
from pathlib import Path

import httpx

from sudroid.errors import ToolMissingError
from sudroid.paths import cache_dir

log = logging.getLogger(__name__)

PLATFORM_TOOLS_URL = {
    "linux": "https://dl.google.com/android/repository/platform-tools-latest-linux.zip",
    "darwin": "https://dl.google.com/android/repository/platform-tools-latest-darwin.zip",
    "windows": "https://dl.google.com/android/repository/platform-tools-latest-windows.zip",
}

DOWNLOADABLE = {"adb", "fastboot"}


def host_os() -> str:
    s = sys.platform
    if s.startswith("linux"):
        return "linux"
    if s == "darwin":
        return "darwin"
    if s.startswith(("win", "cygwin", "msys")):
        return "windows"
    return s


def host_arch() -> str:
    m = platform.machine().lower()
    if m in {"x86_64", "amd64"}:
        return "x86_64"
    if m in {"aarch64", "arm64"}:
        return "arm64"
    if m in {"i386", "i686", "x86"}:
        return "x86"
    return m


def _exe(name: str) -> str:
    return f"{name}.exe" if host_os() == "windows" else name


def common_dirs() -> list[Path]:
    home = Path.home()
    dirs = [
        cache_dir() / "platform-tools",
        home / "Android" / "Sdk" / "platform-tools",
        home / "Library" / "Android" / "sdk" / "platform-tools",
        home / "platform-tools",
        Path("/opt/homebrew/bin"),
        Path("/usr/local/bin"),
        Path("/opt/platform-tools"),
    ]
    local = os.environ.get("LOCALAPPDATA")
    if local:
        dirs.append(Path(local) / "Android" / "Sdk" / "platform-tools")
    sdk = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    if sdk:
        dirs.insert(1, Path(sdk) / "platform-tools")
    return dirs


def locate(name: str, override: str = "", extra_dirs: Sequence[Path] = ()) -> Path | None:
    if override:
        p = Path(override).expanduser()
        if p.is_file():
            return p
        found = shutil.which(override)
        if found:
            return Path(found)
        return None
    found = shutil.which(name)
    if found:
        return Path(found)
    for d in [*extra_dirs, *common_dirs()]:
        candidate = d / _exe(name)
        if candidate.is_file():
            return candidate
    return None


def download_platform_tools(client: httpx.Client, dest: Path, url: str | None = None) -> Path:
    """Download and extract platform-tools into dest. Returns dir containing adb."""
    url = url or PLATFORM_TOOLS_URL.get(host_os())
    if not url:
        raise ToolMissingError(f"No platform-tools download for OS {host_os()}")
    dest.mkdir(parents=True, exist_ok=True)
    log.info("downloading %s", url)
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        with client.stream("GET", url, follow_redirects=True, timeout=120) as r:
            r.raise_for_status()
            for chunk in r.iter_bytes():
                tmp.write(chunk)
    try:
        with zipfile.ZipFile(tmp_path) as zf:
            for info in zf.infolist():
                target = (dest / info.filename).resolve()
                if not str(target).startswith(str(dest.resolve())):
                    raise ToolMissingError(f"unsafe path in archive: {info.filename}")
            zf.extractall(dest)
            if host_os() != "windows":
                for info in zf.infolist():
                    mode = (info.external_attr >> 16) & 0o777
                    target = dest / info.filename
                    if target.is_file() and (mode & 0o111 or target.name in DOWNLOADABLE):
                        target.chmod(
                            target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
                        )
    finally:
        tmp_path.unlink(missing_ok=True)
    out = dest / "platform-tools"
    return out if out.is_dir() else dest


def ensure(
    name: str,
    *,
    override: str = "",
    auto_download: bool = True,
    client: httpx.Client | None = None,
    cache: Path | None = None,
) -> Path:
    found = locate(name, override)
    if found:
        return found
    if name in DOWNLOADABLE and auto_download:
        cache = cache or cache_dir()
        own = client is None
        client = client or httpx.Client()
        try:
            out = download_platform_tools(client, cache)
        finally:
            if own:
                client.close()
        candidate = out / _exe(name)
        if candidate.is_file():
            return candidate
    hint = {
        "adb": "Install Android platform-tools or allow auto download (tools.auto_download).",
        "fastboot": "Install Android platform-tools or allow auto download (tools.auto_download).",
        "heimdall": "Install Heimdall: Debian/Ubuntu 'apt install heimdall-flash', "
        "macOS 'brew install heimdall', Windows: Heimdall Suite zip.",
    }.get(name, f"Install {name} and put it on PATH.")
    raise ToolMissingError(f"{name} not found", hint=hint)


def version(path: Path, name: str) -> str:
    from sudroid.tools.base import SubprocessRunner

    flag = {"adb": "version", "fastboot": "--version", "heimdall": "version"}.get(name, "--version")
    r = SubprocessRunner().run([str(path), flag], timeout=15)
    for line in r.combined.splitlines():
        if line.strip():
            return line.strip()
    return "unknown"
