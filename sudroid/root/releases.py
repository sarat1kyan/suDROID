"""Magisk release lookup and APK download."""

from __future__ import annotations

import hashlib
import logging
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path

import httpx

from sudroid.errors import PatchError

log = logging.getLogger(__name__)

CHANNEL_URLS = {
    "stable": "https://github.com/topjohnwu/magisk-files/raw/master/stable.json",
    "beta": "https://github.com/topjohnwu/magisk-files/raw/master/beta.json",
    "canary": "https://github.com/topjohnwu/magisk-files/raw/master/canary.json",
    "debug": "https://github.com/topjohnwu/magisk-files/raw/master/debug.json",
}
RELEASE_APK = "https://github.com/topjohnwu/Magisk/releases/download/{tag}/Magisk-{tag}.apk"
_TAG = re.compile(r"^v?\d+(\.\d+)*$")


@dataclass(frozen=True)
class MagiskRelease:
    version: str
    version_code: int
    apk_url: str
    channel: str

    @property
    def tag(self) -> str:
        return self.version if self.version.startswith("v") else f"v{self.version}"

    @property
    def filename(self) -> str:
        return f"Magisk-{self.tag}-{self.version_code}.apk"


def fetch_release(client: httpx.Client, channel: str = "stable", pinned: str = "") -> MagiskRelease:
    if pinned:
        if not _TAG.match(pinned):
            raise PatchError(f"bad pinned Magisk version: {pinned}", hint="Use a tag like v27.0")
        tag = pinned if pinned.startswith("v") else f"v{pinned}"
        return MagiskRelease(tag, 0, RELEASE_APK.format(tag=tag), "pinned")
    url = CHANNEL_URLS.get(channel)
    if not url:
        raise PatchError(f"unknown Magisk channel: {channel}", hint="stable, beta, canary, debug")
    r = client.get(url, follow_redirects=True, timeout=30)
    r.raise_for_status()
    data = r.json()
    m = data.get("magisk", {})
    version = str(m.get("version", "")).strip()
    link = str(m.get("link", "")).strip()
    try:
        code = int(m.get("versionCode", 0))
    except (TypeError, ValueError):
        code = 0
    if not version or not link:
        raise PatchError(f"malformed Magisk channel data from {url}")
    log.info("Magisk %s channel: %s (%d)", channel, version, code)
    return MagiskRelease(version, code, link, channel)


def download_apk(client: httpx.Client, rel: MagiskRelease, cache: Path) -> Path:
    cache.mkdir(parents=True, exist_ok=True)
    dest = cache / rel.filename
    sidecar = dest.with_suffix(".apk.sha256")
    if dest.is_file() and sidecar.is_file():
        if sidecar.read_text().strip() == _sha256(dest):
            log.info("using cached %s", dest.name)
            return dest
        log.warning("cached %s failed checksum, re-downloading", dest.name)
    log.info("downloading %s", rel.apk_url)
    tmp = dest.with_suffix(".part")
    with client.stream("GET", rel.apk_url, follow_redirects=True, timeout=300) as r:
        r.raise_for_status()
        with tmp.open("wb") as fh:
            for chunk in r.iter_bytes():
                fh.write(chunk)
    validate_apk(tmp)
    tmp.replace(dest)
    sidecar.write_text(_sha256(dest))
    return dest


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_apk(path: Path) -> None:
    try:
        with zipfile.ZipFile(path) as zf:
            names = set(zf.namelist())
    except zipfile.BadZipFile as exc:
        raise PatchError(f"{path.name} is not a valid APK: {exc}") from None
    if "assets/boot_patch.sh" not in names:
        raise PatchError(f"{path.name} has no assets/boot_patch.sh; not a Magisk APK")
    if not any(n.startswith("lib/") and n.endswith("/libmagiskboot.so") for n in names):
        raise PatchError(f"{path.name} has no libmagiskboot.so; not a Magisk APK")
