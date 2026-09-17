"""Error hierarchy. Each error carries the process exit code."""

from __future__ import annotations


class SudroidError(Exception):
    exit_code = 1

    def __init__(self, message: str, *, hint: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint


class UsageError(SudroidError):
    exit_code = 2


class NoDeviceError(SudroidError):
    exit_code = 10


class MultipleDevicesError(SudroidError):
    exit_code = 11


class ToolMissingError(SudroidError):
    exit_code = 12


class PreconditionError(SudroidError):
    exit_code = 20


class UserAbortError(SudroidError):
    exit_code = 30


class PatchError(SudroidError):
    exit_code = 40


class FlashError(SudroidError):
    exit_code = 50
