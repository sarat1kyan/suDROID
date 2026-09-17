"""Stateful fake device for end to end command tests."""

from __future__ import annotations

import io
import json
import struct
import zipfile
from pathlib import Path

import httpx
import pytest

from sudroid import cli
from sudroid.root.device_patch import REMOTE_DIR
from sudroid.tools import platform_tools
from sudroid.tools.base import FakeRunner, Result
from sudroid.workflow import steps
from tests.conftest import getprop_text


def boot_image(ramdisk: int = 10, kernel: int = 5, version: int = 2) -> bytes:
    h = bytearray(4096)
    h[:8] = b"ANDROID!"
    struct.pack_into("<I", h, 8, kernel)
    if version >= 3:
        struct.pack_into("<I", h, 12, ramdisk)
    else:
        struct.pack_into("<I", h, 16, ramdisk)
    struct.pack_into("<I", h, 40, version)
    return bytes(h)


def fake_apk() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("assets/boot_patch.sh", "#!/system/bin/sh\n")
        zf.writestr("assets/util_functions.sh", "\n")
        zf.writestr("assets/stub.apk", b"PK")
        for abi in ("arm64-v8a", "armeabi-v7a"):
            for lib in ("magiskboot", "magiskinit", "magisk", "init-ld"):
                zf.writestr(f"lib/{abi}/lib{lib}.so", b"x")
    return buf.getvalue()


class FakeDevice:
    """Scripted adb + fastboot behaviour with a mode state machine."""

    def __init__(
        self,
        fixture: str,
        serial: str = "S",
        byname: str = "boot_a boot_b",
        battery: int = 80,
        rooted_after_boot: bool = True,
    ) -> None:
        self.serial = serial
        self.mode = "android"
        self.flashed: list[tuple[str, str]] = []
        self.booted: list[str] = []
        self.rooted = False
        self.rooted_after_boot = rooted_after_boot
        self.runner = FakeRunner()
        fk = self.runner
        s = serial
        fk.on(("adb", "start-server"), "")
        fk.on(
            ("adb", "devices"),
            lambda a: Result(
                a,
                0,
                "List of devices attached\n" + (f"{s}\tdevice\n" if self.mode == "android" else ""),
                "",
                0.0,
            ),
        )
        fk.on(("adb", "-s", s, "shell", "getprop"), getprop_text(fixture))
        fk.on_prefix(("adb", "-s", s, "shell", "ls /dev/block/by-name"), byname)
        fk.on_prefix(("adb", "-s", s, "shell", "command -v"), "no")
        fk.on(("adb", "-s", s, "shell", "dumpsys battery"), f"  level: {battery}\n")
        fk.on(("adb", "-s", s, "reboot", "bootloader"), self._reboot_bl)
        fk.on(("adb", "-s", s, "wait-for-device"), "")
        fk.on(("adb", "-s", s, "shell", "getprop sys.boot_completed"), "1")
        fk.on(
            ("adb", "-s", s, "shell", "su -c id"),
            lambda a: Result(
                a, 0, "uid=0(root) gid=0(root)" if self.rooted else "su: not found", "", 0.0
            ),
        )
        fk.on(("adb", "-s", s, "shell", "su -c 'magisk -v'"), "28.0:MAGISK")
        fk.on(
            ("adb", "-s", s, "shell", "su -c 'ksud -V'"),
            lambda a: Result(a, 127, "", "not found", 0.0),
        )
        fk.on(
            ("adb", "-s", s, "shell", "su -c 'apd -V'"),
            lambda a: Result(a, 127, "", "not found", 0.0),
        )
        fk.on_prefix(("adb", "-s", s, "install"), "Success")
        # device side patching
        fk.on_prefix(("adb", "-s", s, "shell", "rm -rf"), "")
        fk.on_prefix(("adb", "-s", s, "push"), "1 file pushed")
        fk.on_prefix(("adb", "-s", s, "shell", "chmod"), "")
        fk.on_prefix(
            ("adb", "-s", s, "shell", f"cd {REMOTE_DIR} &&"),
            "- Installing: 28.0 (28000)\n- Repacking boot image\n",
        )
        fk.on(("adb", "-s", s, "shell", f"ls {REMOTE_DIR}"), "new-boot.img\nstock.img\n")
        fk.on_prefix(("adb", "-s", s, "pull"), self._pull)
        # fastboot (no -s: ctx.serial is None)
        fk.on(
            ("fastboot", "devices"),
            lambda a: Result(
                a, 0, f"{s}\tfastboot\n" if self.mode == "bootloader" else "", "", 0.0
            ),
        )
        fk.on(
            ("fastboot", "getvar", "current-slot"),
            lambda a: Result(
                a, 0, "", "current-slot: " + self._slot(fixture) + "\nFinished.\n", 0.0
            ),
        )
        fk.on_prefix(("fastboot", "getvar", "partition-type:"), self._parttype)
        fk.on_prefix(("fastboot", "boot"), self._boot)
        fk.on_prefix(("fastboot", "flash"), self._flash)
        fk.on(("fastboot", "reboot"), self._reboot_android)
        self.partitions = set(byname.split())

    @staticmethod
    def _slot(fixture: str) -> str:
        for line in getprop_text(fixture).splitlines():
            if line.startswith("[ro.boot.slot_suffix]"):
                return line.split("[")[-1].rstrip("]")
        return ""

    def _reboot_bl(self, a: tuple[str, ...]) -> Result:
        self.mode = "bootloader"
        return Result(a, 0, "", "", 0.0)

    def _reboot_android(self, a: tuple[str, ...]) -> Result:
        self.mode = "android"
        return Result(a, 0, "", "", 0.0)

    def _boot(self, a: tuple[str, ...]) -> Result:
        self.booted.append(a[-1])
        self.mode = "android"
        self.rooted = self.rooted_after_boot
        return Result(a, 0, "", "Sending 'boot.img' OKAY\nBooting OKAY\n", 0.0)

    def _flash(self, a: tuple[str, ...]) -> Result:
        self.flashed.append((a[-2], a[-1]))
        self.rooted = True
        return Result(a, 0, "", "Writing OKAY\n", 0.0)

    def _parttype(self, a: tuple[str, ...]) -> Result:
        name = a[-1].split(":", 1)[1]
        if name in self.partitions:
            return Result(a, 0, "", f"{a[-1]}: raw\nFinished.\n", 0.0)
        return Result(a, 1, "", f"getvar:{a[-1]} FAILED (remote: 'unknown var')\n", 0.0)

    def _pull(self, a: tuple[str, ...]) -> Result:
        Path(a[-1]).write_bytes(boot_image(ramdisk=99))
        return Result(a, 0, "1 file pulled", "", 0.0)


def install(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, dev: FakeDevice) -> None:
    monkeypatch.setattr(cli, "_make_runner", lambda: dev.runner)
    monkeypatch.setattr(platform_tools, "ensure", lambda name, **kw: Path(name))
    monkeypatch.setenv("SUDROID_GENERAL_LOG_LEVEL", "warning")
    monkeypatch.setenv("SUDROID_GENERAL_BACKUP_DIR", str(tmp_path / "backups"))
    monkeypatch.setattr(cli.config_mod, "default_path", lambda: tmp_path / "none.toml")
    monkeypatch.setattr(steps, "cache_dir", lambda: tmp_path / "cache")
    import sudroid.commands.backup as backup_cmd
    import sudroid.commands.flash as flash_cmd
    import sudroid.commands.patch as patch_cmd
    import sudroid.commands.restore as restore_cmd
    import sudroid.commands.root as root_cmd
    from sudroid.workflow import session as sm

    for mod in (root_cmd, backup_cmd, flash_cmd, patch_cmd, restore_cmd):
        monkeypatch.setattr(mod, "data_dir", lambda: tmp_path / "data")
    monkeypatch.setattr(sm, "sessions_dir", lambda: tmp_path / "sessions")
    payload = {
        "magisk": {"version": "28.0", "versionCode": "28000", "link": "https://x/Magisk-v28.0.apk"}
    }
    apk = fake_apk()

    def handler(req: httpx.Request) -> httpx.Response:
        if str(req.url).endswith(".json"):
            return httpx.Response(200, content=json.dumps(payload).encode())
        return httpx.Response(200, content=apk)

    monkeypatch.setattr(
        steps, "_http_client", lambda: httpx.Client(transport=httpx.MockTransport(handler))
    )
    monkeypatch.setattr("time.sleep", lambda s: None)
