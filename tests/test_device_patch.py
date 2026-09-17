import struct
from pathlib import Path

import pytest

from sudroid.errors import PatchError
from sudroid.root.apk import MagiskBundle
from sudroid.root.device_patch import REMOTE_DIR, DevicePatcher, PatchOptions
from sudroid.tools.adb import AdbClient
from sudroid.tools.base import FakeRunner, Result


def boot(ramdisk: int = 10) -> bytes:
    h = bytearray(4096)
    h[:8] = b"ANDROID!"
    struct.pack_into("<I", h, 8, 5)
    struct.pack_into("<I", h, 16, ramdisk)
    struct.pack_into("<I", h, 40, 2)
    return bytes(h)


def bundle(tmp_path: Path) -> MagiskBundle:
    d = tmp_path / "bundle"
    d.mkdir()
    files = (
        "boot_patch.sh",
        "util_functions.sh",
        "magiskboot",
        "magiskinit",
        "magisk",
        "stub.apk",
        "magisk.apk",
    )
    for f in files:
        (d / f).write_bytes(b"x")
    return MagiskBundle(d, "v28.0", "arm64-v8a", files)


def test_patch_happy_path(tmp_path: Path) -> None:
    stock = tmp_path / "stock.img"
    stock.write_bytes(boot())
    out = tmp_path / "patched.img"
    fk = FakeRunner()
    fk.on_prefix(("adb", "-s", "S", "shell", "rm -rf"), "")
    fk.on_prefix(("adb", "-s", "S", "push"), "1 file pushed")
    fk.on_prefix(("adb", "-s", "S", "shell", "chmod"), "")
    fk.on_prefix(
        ("adb", "-s", "S", "shell", f"cd {REMOTE_DIR} &&"),
        "- Target image: ./stock.img\n- Device platform: arm64-v8a\n"
        "- Installing: 28.0 (28000)\n- Unpacking boot image\n- Repacking boot image\n",
    )
    fk.on(
        ("adb", "-s", "S", "shell", f"ls {REMOTE_DIR}"), "boot_patch.sh\nnew-boot.img\nstock.img\n"
    )

    def pull(args: tuple[str, ...]) -> Result:
        Path(args[-1]).write_bytes(boot(ramdisk=99))
        return Result(args, 0, "1 file pulled", "", 0.0)

    fk.on_prefix(("adb", "-s", "S", "pull"), pull)

    res = DevicePatcher(AdbClient(fk, "adb", "S"), bundle(tmp_path)).patch(
        stock, out, PatchOptions()
    )
    assert res.image == out and out.is_file()
    assert res.magisk_version == "28.0"
    shell_cmd = next(c for c in fk.mutating_calls if c[3] == "shell" and c[4].startswith("cd "))
    assert "KEEPVERITY=true" in shell_cmd[4] and "PATCHVBMETAFLAG=false" in shell_cmd[4]
    assert "sh ./boot_patch.sh ./stock.img" in shell_cmd[4]
    pushed = [c[4] for c in fk.calls if c[3] == "push"]
    assert not any(p.endswith("magisk.apk") for p in pushed)
    assert fk.mutating_calls[-1][4].startswith("rm -rf")


def test_patch_rejects_non_boot(tmp_path: Path) -> None:
    stock = tmp_path / "x.img"
    stock.write_bytes(b"nope" * 100)
    fk = FakeRunner()
    with pytest.raises(PatchError):
        DevicePatcher(AdbClient(fk, "adb", "S"), bundle(tmp_path)).patch(stock, tmp_path / "o.img")
    assert fk.calls == []


def test_patch_script_failure_shows_tail(tmp_path: Path) -> None:
    stock = tmp_path / "stock.img"
    stock.write_bytes(boot())
    fk = FakeRunner()
    fk.on_prefix(("adb", "-s", "S", "shell", "rm -rf"), "")
    fk.on_prefix(("adb", "-s", "S", "push"), "ok")
    fk.on_prefix(("adb", "-s", "S", "shell", "chmod"), "")
    fk.on_prefix(
        ("adb", "-s", "S", "shell", f"cd {REMOTE_DIR} &&"),
        lambda a: Result(
            a, 1, "- Unpacking boot image\n! Unsupported/Unknown image format\n", "", 0.0
        ),
    )
    fk.on(("adb", "-s", "S", "shell", f"ls {REMOTE_DIR}"), "stock.img\n")
    with pytest.raises(PatchError) as ei:
        DevicePatcher(AdbClient(fk, "adb", "S"), bundle(tmp_path)).patch(stock, tmp_path / "o.img")
    assert "Unsupported" in (ei.value.hint or "")
    assert fk.mutating_calls[-1][4].startswith("rm -rf")


def test_patch_options_env() -> None:
    e = PatchOptions(keep_verity=False, recovery_mode=True).env()
    assert "KEEPVERITY=false" in e and "RECOVERYMODE=true" in e and "LEGACYSAR=false" in e
