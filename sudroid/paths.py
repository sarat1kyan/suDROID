"""Per-user directories."""

from __future__ import annotations

from pathlib import Path

from platformdirs import PlatformDirs

_dirs = PlatformDirs(appname="sudroid", appauthor=False)


def cache_dir() -> Path:
    return Path(_dirs.user_cache_dir)


def config_dir() -> Path:
    return Path(_dirs.user_config_dir)


def state_dir() -> Path:
    return Path(_dirs.user_state_dir)


def data_dir() -> Path:
    return Path(_dirs.user_data_dir)


def sessions_dir() -> Path:
    return data_dir() / "sessions"
