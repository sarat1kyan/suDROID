"""KernelSU: prebuilt GKI kernels flashed to boot."""

from __future__ import annotations

import gzip
import re
import shutil
from pathlib import Path

from sudroid.root.github import Release

REPO = "tiann/KernelSU"
_KMI = re.compile(r"^(?P<ver>\d+\.\d+)\.\d+-(?P<android>android\d+)-(?P<gen>\d+)")


def kmi_of(kernel_release: str) -> str | None:
    """'5.10.209-android12-9-00001-gabc' -> 'android12-5.10'."""
    m = _KMI.match(kernel_release.strip())
    if not m:
        return None
    return f"{m.group('android')}-{m.group('ver')}"


def match_boot_asset(rel: Release, kmi: str) -> tuple[str, str] | None:
    """Return (asset name, url) of the plain boot.img.gz for this KMI."""
    android, ver = kmi.split("-", 1)
    candidates: list[tuple[str, str]] = []
    for name, url in rel.assets.items():
        low = name.lower()
        if not low.endswith("-boot.img.gz") and not low.endswith("boot.img.gz"):
            continue
        if android in low and f"-{ver}." in low and "lz4" not in low and "gz-" not in low:
            candidates.append((name, url))
    if not candidates:
        return None
    candidates.sort()
    return candidates[-1]


def manager_apk(rel: Release) -> str | None:
    return rel.find("kernelsu", ".apk", exclude=("debug",)) or rel.find(".apk")


def gunzip(src: Path, dest: Path) -> Path:
    with gzip.open(src, "rb") as fh, dest.open("wb") as out:
        shutil.copyfileobj(fh, out)
    return dest


def steps_manual() -> list[str]:
    return [
        "Non GKI kernel: KernelSU needs a kernel built with KernelSU for this exact device",
        "Find a KernelSU kernel for your model on the KernelSU site or XDA, get the boot image",
        "Run: sudroid flash <kernelsu_boot.img> --partition boot --test-boot",
        "Install the KernelSU manager APK, confirm with `sudroid verify`",
    ]
