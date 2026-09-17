"""Subprocess abstraction. Only this package spawns processes.

Every device write is flagged with mutating=True so DryRunRunner can
refuse it and tests can assert on it.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Protocol

log = logging.getLogger(__name__)

Args = tuple[str, ...]


@dataclass(frozen=True)
class Result:
    args: Args
    returncode: int
    stdout: str
    stderr: str
    duration: float

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    @property
    def text(self) -> str:
        return self.stdout.replace("\r\n", "\n").replace("\r", "\n").strip()

    @property
    def err(self) -> str:
        return self.stderr.replace("\r\n", "\n").replace("\r", "\n").strip()

    @property
    def combined(self) -> str:
        return (self.text + "\n" + self.err).strip()


class Runner(Protocol):
    def run(
        self,
        args: Sequence[str],
        *,
        timeout: float = 60,
        mutating: bool = False,
        input: bytes | None = None,
    ) -> Result: ...


def _truncate(s: str, n: int = 400) -> str:
    return s if len(s) <= n else s[:n] + "...(truncated)"


class SubprocessRunner:
    """Real process execution."""

    def run(
        self,
        args: Sequence[str],
        *,
        timeout: float = 60,
        mutating: bool = False,
        input: bytes | None = None,
    ) -> Result:
        argv = tuple(str(a) for a in args)
        start = time.monotonic()
        if shutil.which(argv[0]) is None:
            res = Result(argv, 127, "", f"{argv[0]}: command not found", 0.0)
            log.debug("run %s -> 127 (not found)", argv)
            return res
        try:
            proc = subprocess.run(
                argv,
                input=input,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
            out = proc.stdout.decode("utf-8", errors="replace")
            err = proc.stderr.decode("utf-8", errors="replace")
            code = proc.returncode
        except subprocess.TimeoutExpired as exc:
            out = (exc.stdout or b"").decode("utf-8", errors="replace")
            err = (exc.stderr or b"").decode("utf-8", errors="replace")
            err += f"\ntimeout after {timeout}s"
            code = 124
        duration = time.monotonic() - start
        res = Result(argv, code, out, err, duration)
        log.debug(
            "run %s mutating=%s -> %d in %.2fs stdout=%r stderr=%r",
            " ".join(argv),
            mutating,
            code,
            duration,
            _truncate(res.text),
            _truncate(res.err),
        )
        return res


class DryRunRunner:
    """Executes read-only commands, records and skips mutating ones."""

    def __init__(self, inner: Runner) -> None:
        self._inner = inner
        self.recorded: list[Args] = []

    def run(
        self,
        args: Sequence[str],
        *,
        timeout: float = 60,
        mutating: bool = False,
        input: bytes | None = None,
    ) -> Result:
        argv = tuple(str(a) for a in args)
        if mutating:
            self.recorded.append(argv)
            log.info("dry-run: %s", " ".join(argv))
            return Result(argv, 0, "", "", 0.0)
        return self._inner.run(argv, timeout=timeout, mutating=False, input=input)


Response = str | Result | Callable[[Args], Result]


def _prefix_matches(prefix: Args, argv: Args) -> bool:
    """All prefix elements equal, except the last which may be a string prefix."""
    if len(prefix) > len(argv) or not prefix:
        return False
    head, last = prefix[:-1], prefix[-1]
    return argv[: len(head)] == head and argv[len(head)].startswith(last)


@dataclass
class FakeRunner:
    """Test double. Exact-match responses first, then prefix matches."""

    responses: dict[Args, Response] = field(default_factory=dict)
    prefixes: list[tuple[Args, Response]] = field(default_factory=list)
    calls: list[Args] = field(default_factory=list)
    mutating_calls: list[Args] = field(default_factory=list)

    def on(self, args: Sequence[str], response: Response) -> None:
        self.responses[tuple(args)] = response

    def on_prefix(self, prefix: Sequence[str], response: Response) -> None:
        self.prefixes.append((tuple(prefix), response))

    def run(
        self,
        args: Sequence[str],
        *,
        timeout: float = 60,
        mutating: bool = False,
        input: bytes | None = None,
    ) -> Result:
        argv = tuple(str(a) for a in args)
        self.calls.append(argv)
        if mutating:
            self.mutating_calls.append(argv)
        response = self.responses.get(argv)
        if response is None:
            for prefix, resp in self.prefixes:
                if _prefix_matches(prefix, argv):
                    response = resp
                    break
        if response is None:
            raise KeyError(f"FakeRunner has no response for: {' '.join(argv)}")
        if isinstance(response, str):
            return Result(argv, 0, response, "", 0.0)
        if isinstance(response, Result):
            return response
        return response(argv)
