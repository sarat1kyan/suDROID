"""Dispatch a firmware archive to the right extractor."""

from __future__ import annotations

import logging
import shutil
import zipfile
from collections.abc import Iterable
from pathlib import Path

from sudroid.errors import PreconditionError
from sudroid.images import factory, payload, samsung

log = logging.getLogger(__name__)


def kind_of(archive: Path) -> str:
    name = archive.name.lower()
    if name.endswith((".tar", ".tar.md5")):
        return "samsung-ap"
    if name.endswith(".bin"):
        return "payload"
    if name.endswith(".img"):
        return "image"
    if name.endswith(".zip"):
        try:
            with zipfile.ZipFile(archive) as zf:
                names = zf.namelist()
        except zipfile.BadZipFile:
            raise PreconditionError(f"{archive.name} is not a valid zip") from None
        if "payload.bin" in names:
            return "ota"
        return "factory"
    raise PreconditionError(
        f"unknown firmware archive type: {archive.name}",
        hint="Supported: OTA zip (payload.bin), factory zip, payload.bin, Samsung AP tar, raw .img",
    )


def extract_firmware(archive: Path, names: Iterable[str], dest: Path) -> dict[str, Path]:
    if not archive.is_file():
        raise PreconditionError(f"firmware archive not found: {archive}")
    wanted = [n if n.endswith(".img") else f"{n}.img" for n in names]
    kind = kind_of(archive)
    log.info("firmware %s detected as %s", archive.name, kind)
    dest.mkdir(parents=True, exist_ok=True)
    if kind == "samsung-ap":
        return samsung.extract_ap(archive, dest, names=wanted)
    if kind == "payload":
        return payload.extract_from_file(archive, wanted, dest)
    if kind == "ota":
        return payload.extract_from_zip(archive, wanted, dest)
    if kind == "factory":
        return factory.extract_factory(archive, wanted, dest)
    out = dest / archive.name
    shutil.copy2(archive, out)
    return {archive.name: out}
