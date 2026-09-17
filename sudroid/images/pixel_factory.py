"""Locate and download Google factory images for Pixel devices."""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from pathlib import Path

import httpx

from sudroid.errors import PreconditionError

log = logging.getLogger(__name__)

FACTORY_PAGE = "https://developers.google.com/android/images"
OTA_PAGE = "https://developers.google.com/android/ota"
_LINK = re.compile(
    r"https://dl\.google\.com/dl/android/aosp/(?P<codename>[a-z0-9_]+)-(?P<build>[a-z0-9.]+)-"
    r"(?P<kind>factory|ota)-(?P<short>[0-9a-f]{8})\.zip"
)
_SHA = re.compile(r"\b[0-9a-f]{64}\b")


@dataclass(frozen=True)
class FactoryImage:
    codename: str
    build_id: str
    url: str
    sha256: str
    kind: str = "factory"

    @property
    def filename(self) -> str:
        return self.url.rsplit("/", 1)[-1]


def find_image(
    html: str, codename: str, build_id: str, kind: str = "factory"
) -> FactoryImage | None:
    want_build = build_id.lower()
    for m in _LINK.finditer(html):
        if m.group("codename") != codename.lower() or m.group("kind") != kind:
            continue
        if m.group("build") != want_build:
            continue
        # sha256 sits in the same table row, right after the link
        tail = html[m.end() : m.end() + 2000]
        sha = _SHA.search(tail)
        return FactoryImage(codename, build_id, m.group(0), sha.group(0) if sha else "", kind)
    return None


def list_builds(html: str, codename: str, kind: str = "factory") -> list[str]:
    return sorted(
        {
            m.group("build").upper()
            for m in _LINK.finditer(html)
            if m.group("codename") == codename.lower() and m.group("kind") == kind
        }
    )


def fetch_page(client: httpx.Client, kind: str = "factory") -> str:
    url = FACTORY_PAGE if kind == "factory" else OTA_PAGE
    r = client.get(url, follow_redirects=True, timeout=60)
    r.raise_for_status()
    return r.text


def download(client: httpx.Client, image: FactoryImage, cache: Path) -> Path:
    cache.mkdir(parents=True, exist_ok=True)
    dest = cache / image.filename
    sidecar = dest.with_suffix(".zip.sha256")
    if dest.is_file() and sidecar.is_file() and sidecar.read_text().strip() == image.sha256:
        log.info("using cached %s", dest.name)
        return dest
    tmp = dest.with_suffix(".part")
    digest = hashlib.sha256()
    log.info("downloading %s", image.url)
    with client.stream("GET", image.url, follow_redirects=True, timeout=600) as r:
        r.raise_for_status()
        with tmp.open("wb") as fh:
            for chunk in r.iter_bytes(1 << 20):
                fh.write(chunk)
                digest.update(chunk)
    if image.sha256 and digest.hexdigest() != image.sha256:
        tmp.unlink(missing_ok=True)
        raise PreconditionError(
            f"sha256 mismatch for {image.filename}", hint="Download again or use --firmware."
        )
    tmp.replace(dest)
    sidecar.write_text(image.sha256)
    return dest
