"""Console and file logging."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler

from sudroid.paths import state_dir

_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "warn": logging.WARNING,
    "error": logging.ERROR,
}


def default_log_file() -> Path:
    return state_dir() / "sudroid.log"


def setup(
    level: str = "info",
    *,
    json_mode: bool = False,
    log_file: Path | None = None,
    no_color: bool = False,
) -> Console:
    """Configure root logger. Returns the console for human output.

    In json mode human output goes to stderr so stdout stays machine readable.
    """
    console = Console(stderr=json_mode, no_color=no_color, highlight=False)
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
    root.setLevel(logging.DEBUG)

    rich_handler = RichHandler(
        console=console,
        show_time=False,
        show_path=False,
        rich_tracebacks=False,
        markup=False,
    )
    rich_handler.setLevel(_LEVELS.get(level.lower(), logging.INFO))
    root.addHandler(rich_handler)

    if log_file is None:
        log_file = default_log_file()
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        fh = RotatingFileHandler(log_file, maxBytes=2_000_000, backupCount=5, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s"))
        root.addHandler(fh)
    except OSError as exc:  # pragma: no cover
        print(f"warning: cannot open log file {log_file}: {exc}", file=sys.stderr)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    return console


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
