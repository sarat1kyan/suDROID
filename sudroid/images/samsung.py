"""Samsung AP firmware tar handling and Odin tar output."""

from __future__ import annotations

import hashlib
import logging
import tarfile
from collections.abc import Iterable
from pathlib import Path

import lz4.frame

from sudroid.errors import PreconditionError

log = logging.getLogger(__name__)

AP_IMAGES: tuple[str, ...] = ("boot.img", "init_boot.img", "vbmeta.img", "recovery.img")
MAX_ENTRY = 512 * 1024 * 1024


def _open(tar_path: Path) -> tarfile.TarFile:
    try:
        return tarfile.open(tar_path, mode="r:*")
    except tarfile.TarError as exc:
        raise PreconditionError(f"{tar_path.name} is not a readable tar: {exc}") from None


def list_ap(tar_path: Path) -> list[str]:
    with _open(tar_path) as tf:
        return [m.name for m in tf.getmembers() if m.isfile()]


def _base_name(entry: str) -> str:
    name = Path(entry).name
    return name[:-4] if name.endswith(".lz4") else name


def extract_ap(tar_path: Path, dest: Path, names: Iterable[str] = AP_IMAGES) -> dict[str, Path]:
    wanted = set(names)
    found: dict[str, Path] = {}
    dest.mkdir(parents=True, exist_ok=True)
    with _open(tar_path) as tf:
        for member in tf:
            if not member.isfile():
                continue
            base = _base_name(member.name)
            if base not in wanted or base in found:
                continue
            if member.size > MAX_ENTRY:
                raise PreconditionError(f"{member.name} is too large ({member.size} bytes)")
            fh = tf.extractfile(member)
            if fh is None:
                continue
            data = fh.read()
            if member.name.endswith(".lz4"):
                try:
                    data = lz4.frame.decompress(data)
                except RuntimeError as exc:
                    raise PreconditionError(
                        f"lz4 decompress of {member.name} failed: {exc}"
                    ) from None
            out = dest / base
            out.write_bytes(data)
            found[base] = out
            log.info("extracted %s (%d bytes)", base, len(data))
    if not found:
        raise PreconditionError(
            f"no boot, init_boot or vbmeta image found in {tar_path.name}",
            hint="Use the AP_*.tar.md5 file from the firmware package for the installed build.",
        )
    return found


def build_odin_tar(images: dict[str, Path], out: Path) -> Path:
    """Write an Odin flashable AP tar with raw images and the .md5 trailer."""
    out.parent.mkdir(parents=True, exist_ok=True)
    tar_path = out.with_suffix("") if out.suffix == ".md5" else out
    if tar_path.suffix != ".tar":
        tar_path = tar_path.with_suffix(".tar")
    with tarfile.open(tar_path, mode="w", format=tarfile.USTAR_FORMAT) as tf:
        for name, path in images.items():
            info = tarfile.TarInfo(name=name)
            info.size = path.stat().st_size
            info.mode = 0o644
            info.mtime = int(path.stat().st_mtime)
            with path.open("rb") as fh:
                tf.addfile(info, fh)
    md5 = hashlib.md5(usedforsecurity=False)
    with tar_path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            md5.update(chunk)
    final = tar_path.with_name(tar_path.name + ".md5")
    with tar_path.open("rb") as src, final.open("wb") as dst:
        for chunk in iter(lambda: src.read(1 << 20), b""):
            dst.write(chunk)
        dst.write(f"{md5.hexdigest()}  {tar_path.name}\n".encode())
    tar_path.unlink()
    log.info("wrote Odin tar %s", final)
    return final
