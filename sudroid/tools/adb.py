"""adb client. Read operations are non-mutating; push/install/reboot are mutating."""

from __future__ import annotations

import logging
import shlex
import time
from dataclasses import dataclass
from pathlib import Path

from sudroid.device.props import Props
from sudroid.tools.base import Result, Runner

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class AdbDevice:
    serial: str
    state: str  # device, unauthorized, offline, recovery, sideload, bootloader

    @property
    def ready(self) -> bool:
        return self.state == "device"


class AdbClient:
    def __init__(self, runner: Runner, path: str = "adb", serial: str | None = None) -> None:
        self._runner = runner
        self._path = path
        self.serial = serial

    def _base(self) -> list[str]:
        args = [self._path]
        if self.serial:
            args += ["-s", self.serial]
        return args

    def _run(self, *args: str, timeout: float = 60, mutating: bool = False) -> Result:
        return self._runner.run([*self._base(), *args], timeout=timeout, mutating=mutating)

    def version(self) -> str:
        r = self._runner.run([self._path, "version"], timeout=15)
        for line in r.text.splitlines():
            if "version" in line.lower():
                return line.strip()
        return r.text.splitlines()[0] if r.text else ""

    def start_server(self) -> Result:
        return self._runner.run([self._path, "start-server"], timeout=30)

    def devices(self) -> list[AdbDevice]:
        r = self._runner.run([self._path, "devices"], timeout=30)
        out: list[AdbDevice] = []
        for line in r.text.splitlines():
            if not line.strip() or line.startswith("List of devices") or line.startswith("*"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                out.append(AdbDevice(parts[0], parts[1]))
        return out

    def shell(self, cmd: str, *, timeout: float = 60) -> Result:
        return self._run("shell", cmd, timeout=timeout)

    def getprop_all(self) -> Props:
        return Props.parse(self.shell("getprop", timeout=30).text)

    def getprop(self, key: str) -> str:
        return self.shell(f"getprop {shlex.quote(key)}", timeout=15).text

    def list_byname(self) -> frozenset[str]:
        r = self.shell("ls /dev/block/by-name 2>/dev/null", timeout=15)
        if not r.ok or not r.text:
            return frozenset()
        return frozenset(name.strip() for name in r.text.split() if name.strip())

    def which(self, name: str) -> bool:
        r = self.shell(
            f"command -v {shlex.quote(name)} >/dev/null 2>&1 && echo yes || echo no", timeout=15
        )
        return r.text.strip().endswith("yes")

    def battery_level(self) -> int | None:
        r = self.shell("dumpsys battery", timeout=20)
        for line in r.text.splitlines():
            line = line.strip()
            if line.startswith("level:"):
                try:
                    return int(line.split(":", 1)[1].strip())
                except ValueError:
                    return None
        return None

    def pull(self, remote: str, local: Path, *, timeout: float = 600) -> Result:
        return self._run("pull", remote, str(local), timeout=timeout)

    def push(self, local: Path, remote: str, *, timeout: float = 600) -> Result:
        return self._run("push", str(local), remote, timeout=timeout, mutating=True)

    def install(self, apk: Path, *, timeout: float = 300) -> Result:
        return self._run("install", "-r", str(apk), timeout=timeout, mutating=True)

    def reboot(self, target: str = "") -> Result:
        args = ["reboot"] + ([target] if target else [])
        return self._run(*args, timeout=30, mutating=True)

    def wait_for_device(self, timeout: float = 180) -> Result:
        return self._run("wait-for-device", timeout=timeout)

    def wait_for_ready(self, timeout: float = 240) -> bool:
        """Wait until boot completes (sys.boot_completed=1)."""
        deadline = time.monotonic() + timeout
        self.wait_for_device(timeout=timeout)
        while time.monotonic() < deadline:
            if self.getprop("sys.boot_completed") == "1":
                return True
            time.sleep(2)
        return False

    def root_shell(self, cmd: str, *, timeout: float = 60) -> Result:
        return self._run("shell", f"su -c {shlex.quote(cmd)}", timeout=timeout)
