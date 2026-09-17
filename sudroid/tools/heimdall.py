"""Heimdall client for Samsung download mode."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from sudroid.tools.base import Result, Runner

log = logging.getLogger(__name__)


class HeimdallClient:
    def __init__(self, runner: Runner, path: str = "heimdall") -> None:
        self._runner = runner
        self._path = path

    def version(self) -> str:
        r = self._runner.run([self._path, "version"], timeout=15)
        return r.combined.splitlines()[0] if r.combined else ""

    def detect(self) -> bool:
        r = self._runner.run([self._path, "detect"], timeout=30)
        return r.ok

    def print_pit(self) -> list[str]:
        r = self._runner.run([self._path, "print-pit", "--no-reboot"], timeout=120)
        names: list[str] = []
        for line in r.combined.splitlines():
            line = line.strip()
            if line.lower().startswith("partition name:"):
                name = line.split(":", 1)[1].strip()
                if name:
                    names.append(name)
        return names

    def flash(
        self, images: dict[str, Path], *, no_reboot: bool = False, timeout: float = 900
    ) -> Result:
        args = [self._path, "flash"]
        for partition, path in images.items():
            args += [f"--{partition}", str(path)]
        if no_reboot:
            args.append("--no-reboot")
        return self._runner.run(args, timeout=timeout, mutating=True)

    def wait(self, timeout: float = 120, poll: float = 2.0) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.detect():
                return True
            time.sleep(poll)
        return False
