"""Boot image header inspection and hashing."""

from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass
from pathlib import Path

BOOT_MAGIC = b"ANDROID!"
VENDOR_BOOT_MAGIC = b"VNDRBOOT"
AVB_MAGIC = b"AVB0"
AVB_FLAGS_OFFSET = 0x78
AVB_FLAG_HASHTREE_DISABLED = 1
AVB_FLAG_VERIFICATION_DISABLED = 2


@dataclass(frozen=True)
class ImageInfo:
    path: Path
    size: int
    sha256: str
    kind: str  # boot, vendor_boot, vbmeta, unknown
    header_version: int
    kernel_size: int
    ramdisk_size: int

    @property
    def has_ramdisk(self) -> bool:
        return self.ramdisk_size > 0

    @property
    def is_boot(self) -> bool:
        return self.kind == "boot"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def inspect(path: Path) -> ImageInfo:
    size = path.stat().st_size
    with path.open("rb") as fh:
        head = fh.read(64)
    kind = "unknown"
    header_version = -1
    kernel_size = 0
    ramdisk_size = 0
    if head[:8] == BOOT_MAGIC and len(head) >= 44:
        kind = "boot"
        # v0-v2: kernel_size@8, ramdisk_size@16 ; v3-v4: kernel_size@8, ramdisk_size@12
        header_version = struct.unpack_from("<I", head, 40)[0]
        kernel_size = struct.unpack_from("<I", head, 8)[0]
        if header_version >= 3:
            ramdisk_size = struct.unpack_from("<I", head, 12)[0]
        else:
            ramdisk_size = struct.unpack_from("<I", head, 16)[0]
        if header_version > 8:
            header_version = -1
    elif head[:8] == VENDOR_BOOT_MAGIC and len(head) >= 12:
        kind = "vendor_boot"
        header_version = struct.unpack_from("<I", head, 8)[0]
    elif head[:4] == AVB_MAGIC:
        kind = "vbmeta"
    return ImageInfo(
        path=path,
        size=size,
        sha256=sha256_file(path),
        kind=kind,
        header_version=header_version,
        kernel_size=kernel_size,
        ramdisk_size=ramdisk_size,
    )


def patch_vbmeta_flags(data: bytes) -> bytes:
    """Set hashtree and verification disabled flags on an AVB vbmeta image."""
    if data[:4] != AVB_MAGIC or len(data) < AVB_FLAGS_OFFSET + 4:
        raise ValueError("not an AVB vbmeta image")
    (flags,) = struct.unpack_from(">I", data, AVB_FLAGS_OFFSET)
    flags |= AVB_FLAG_HASHTREE_DISABLED | AVB_FLAG_VERIFICATION_DISABLED
    out = bytearray(data)
    struct.pack_into(">I", out, AVB_FLAGS_OFFSET, flags)
    return bytes(out)
