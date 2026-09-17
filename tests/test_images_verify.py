import struct
from pathlib import Path

import pytest

from sudroid.images.verify import inspect, patch_vbmeta_flags, sha256_file


def boot_v2(kernel: int = 100, ramdisk: int = 50) -> bytes:
    h = bytearray(4096)
    h[:8] = b"ANDROID!"
    struct.pack_into("<I", h, 8, kernel)
    struct.pack_into("<I", h, 16, ramdisk)
    struct.pack_into("<I", h, 40, 2)
    return bytes(h)


def boot_v4(kernel: int = 0, ramdisk: int = 77) -> bytes:
    h = bytearray(4096)
    h[:8] = b"ANDROID!"
    struct.pack_into("<I", h, 8, kernel)
    struct.pack_into("<I", h, 12, ramdisk)
    struct.pack_into("<I", h, 40, 4)
    return bytes(h)


def test_inspect_v2(tmp_path: Path) -> None:
    p = tmp_path / "boot.img"
    p.write_bytes(boot_v2())
    i = inspect(p)
    assert i.kind == "boot" and i.header_version == 2
    assert i.kernel_size == 100 and i.ramdisk_size == 50
    assert i.has_ramdisk and i.is_boot
    assert i.sha256 == sha256_file(p)


def test_inspect_v4_init_boot_like(tmp_path: Path) -> None:
    p = tmp_path / "init_boot.img"
    p.write_bytes(boot_v4())
    i = inspect(p)
    assert i.header_version == 4 and i.kernel_size == 0 and i.ramdisk_size == 77


def test_inspect_v4_gki_boot_without_ramdisk(tmp_path: Path) -> None:
    p = tmp_path / "boot.img"
    p.write_bytes(boot_v4(kernel=500, ramdisk=0))
    assert inspect(p).has_ramdisk is False


def test_inspect_vendor_boot_and_unknown(tmp_path: Path) -> None:
    v = tmp_path / "vendor_boot.img"
    h = bytearray(64)
    h[:8] = b"VNDRBOOT"
    struct.pack_into("<I", h, 8, 4)
    v.write_bytes(bytes(h))
    assert inspect(v).kind == "vendor_boot"
    assert inspect(v).header_version == 4
    u = tmp_path / "x.img"
    u.write_bytes(b"garbage" * 10)
    assert inspect(u).kind == "unknown"
    assert inspect(u).header_version == -1


def test_vbmeta_flags(tmp_path: Path) -> None:
    data = bytearray(256)
    data[:4] = b"AVB0"
    out = patch_vbmeta_flags(bytes(data))
    assert struct.unpack_from(">I", out, 0x78)[0] == 3
    p = tmp_path / "vbmeta.img"
    p.write_bytes(out)
    assert inspect(p).kind == "vbmeta"
    with pytest.raises(ValueError):
        patch_vbmeta_flags(b"nope")
