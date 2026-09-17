"""Pixel style factory image zips: <codename>-<build>/image-<codename>-<build>.zip."""

from __future__ import annotations

import logging
import zipfile
from collections.abc import Iterable
from pathlib import Path

from sudroid.errors import PreconditionError

log = logging.getLogger(__name__)

MAX_IMAGE = 512 * 1024 * 1024


def _copy_member(zf: zipfile.ZipFile, member: zipfile.ZipInfo, out: Path) -> None:
    if member.file_size > MAX_IMAGE:
        raise PreconditionError(f"{member.filename} is too large ({member.file_size} bytes)")
    out.parent.mkdir(parents=True, exist_ok=True)
    with zf.open(member) as src, out.open("wb") as dst:
        for chunk in iter(lambda: src.read(1 << 20), b""):
            dst.write(chunk)


def extract_images(zf: zipfile.ZipFile, names: set[str], dest: Path) -> dict[str, Path]:
    found: dict[str, Path] = {}
    for member in zf.infolist():
        base = Path(member.filename).name
        if base in names and base not in found and not member.is_dir():
            _copy_member(zf, member, dest / base)
            found[base] = dest / base
            log.info("extracted %s (%d bytes)", base, member.file_size)
    return found


def extract_factory(zip_path: Path, names: Iterable[str], dest: Path) -> dict[str, Path]:
    wanted = set(names)
    try:
        with zipfile.ZipFile(zip_path) as zf:
            found = extract_images(zf, wanted, dest)
            if found:
                return found
            inner = [
                m
                for m in zf.infolist()
                if Path(m.filename).name.startswith("image-") and m.filename.endswith(".zip")
            ]
            if not inner:
                raise PreconditionError(
                    f"no boot images or image-*.zip in {zip_path.name}",
                    hint="Use the factory image zip or a full OTA zip for the installed build.",
                )
            with zf.open(inner[0]) as fh, zipfile.ZipFile(fh) as izf:
                found = extract_images(izf, wanted, dest)
    except zipfile.BadZipFile as exc:
        raise PreconditionError(f"{zip_path.name} is not a valid zip: {exc}") from None
    if not found:
        raise PreconditionError(f"none of {sorted(wanted)} found in {zip_path.name}")
    return found
