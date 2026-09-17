"""fastboot client. getvar output arrives on stderr."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from sudroid.tools.base import Result, Runner

log = logging.getLogger(__name__)


_COMPOUND_KEYS = {
    "has-slot",
    "partition-type",
    "partition-size",
    "is-logical",
    "slot-successful",
    "slot-unbootable",
    "slot-retry-count",
}


def parse_getvar(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in text.replace("\r\n", "\n").split("\n"):
        line = raw.strip()
        if line.startswith("(bootloader)"):
            line = line[len("(bootloader)") :].strip()
        if not line or line.startswith(("Finished", "OKAY", "FAILED", "Total time", "Waiting")):
            continue
        if ":" not in line:
            continue
        head = line.split(":", 1)[0].strip()
        if head in _COMPOUND_KEYS and line.count(":") >= 2:
            key, value = line.rsplit(":", 1)
        else:
            key, value = line.split(":", 1)
        key = key.strip()
        if key and key not in out:
            out[key] = value.strip()
    return out


class FastbootClient:
    def __init__(self, runner: Runner, path: str = "fastboot", serial: str | None = None) -> None:
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
        r = self._runner.run([self._path, "--version"], timeout=15)
        return r.text.splitlines()[0] if r.text else ""

    def devices(self) -> list[str]:
        r = self._runner.run([self._path, "devices"], timeout=30)
        out: list[str] = []
        for line in r.text.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[1] in {"fastboot", "fastbootd"}:
                out.append(parts[0])
        return out

    def getvar(self, name: str) -> str | None:
        r = self._run("getvar", name, timeout=30)
        vars_ = parse_getvar(r.combined)
        return vars_.get(name)

    def getvar_all(self) -> dict[str, str]:
        r = self._run("getvar", "all", timeout=60)
        return parse_getvar(r.combined)

    def current_slot(self) -> str:
        v = self.getvar("current-slot") or ""
        return v.strip().lstrip("_")

    def has_slot(self, partition: str) -> bool:
        v = (self.getvar(f"has-slot:{partition}") or "").lower()
        return v == "yes"

    def unlocked(self) -> bool | None:
        v = (self.getvar("unlocked") or "").lower()
        if v == "yes":
            return True
        if v == "no":
            return False
        return None

    def flash(self, partition: str, image: Path, *, timeout: float = 600) -> Result:
        return self._run("flash", partition, str(image), timeout=timeout, mutating=True)

    def boot(self, image: Path, *, timeout: float = 300) -> Result:
        return self._run("boot", str(image), timeout=timeout, mutating=True)

    def reboot(self, target: str = "") -> Result:
        args = ["reboot"] + ([target] if target else [])
        return self._run(*args, timeout=60, mutating=True)

    def set_active(self, slot: str) -> Result:
        return self._run("set_active", slot, timeout=60, mutating=True)

    def oem(self, *args: str, timeout: float = 120) -> Result:
        return self._run("oem", *args, timeout=timeout, mutating=True)

    def oem_read(self, *args: str, timeout: float = 60) -> Result:
        """oem subcommands that only read (get_unlock_data, device-info)."""
        return self._run("oem", *args, timeout=timeout)

    def flashing(self, *args: str, timeout: float = 120) -> Result:
        return self._run("flashing", *args, timeout=timeout, mutating=True)

    def wait(self, timeout: float = 180, poll: float = 2.0) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            devs = self.devices()
            if devs and (self.serial is None or self.serial in devs):
                return True
            time.sleep(poll)
        return False
