"""TOML config with env overrides. Precedence: defaults < file < SUDROID_* env < CLI."""

from __future__ import annotations

import dataclasses
import logging
import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

from sudroid.paths import config_dir

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib

log = logging.getLogger(__name__)


@dataclass
class GeneralConfig:
    min_battery: int = 50
    backup_dir: str = "~/sudroid-backups"
    log_level: str = "info"


@dataclass
class MagiskConfig:
    channel: str = "stable"
    pinned_version: str = ""
    keep_verity: bool = True
    keep_force_encrypt: bool = True
    patch_vbmeta: bool = False
    recovery_mode: bool = False


@dataclass
class ToolsConfig:
    adb: str = ""
    fastboot: str = ""
    heimdall: str = ""
    auto_download: bool = True


@dataclass
class Config:
    general: GeneralConfig = field(default_factory=GeneralConfig)
    magisk: MagiskConfig = field(default_factory=MagiskConfig)
    tools: ToolsConfig = field(default_factory=ToolsConfig)

    @property
    def backup_dir(self) -> Path:
        return Path(self.general.backup_dir).expanduser()

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def default_path() -> Path:
    return config_dir() / "config.toml"


def _coerce(current: Any, raw: Any) -> Any:
    if isinstance(current, bool):
        if isinstance(raw, bool):
            return raw
        return str(raw).strip().lower() in {"1", "true", "yes", "on"}
    if isinstance(current, int):
        return int(raw)
    return str(raw)


def _apply(section: Any, data: Mapping[str, Any], name: str) -> None:
    known = {f.name for f in fields(section)}
    for key, value in data.items():
        if key not in known:
            log.warning("config: unknown key %s.%s ignored", name, key)
            continue
        try:
            setattr(section, key, _coerce(getattr(section, key), value))
        except (TypeError, ValueError) as exc:
            log.warning("config: bad value for %s.%s: %s", name, key, exc)


def load(path: Path | None = None, env: Mapping[str, str] | None = None) -> Config:
    cfg = Config()
    env = os.environ if env is None else env
    path = path or default_path()
    if path.is_file():
        with path.open("rb") as fh:
            data = tomllib.load(fh)
        for section_name in ("general", "magisk", "tools"):
            section = data.get(section_name)
            if isinstance(section, dict):
                _apply(getattr(cfg, section_name), section, section_name)
        for key in data:
            if key not in {"general", "magisk", "tools"}:
                log.warning("config: unknown section %s ignored", key)
    prefix = "SUDROID_"
    for key, value in env.items():
        if not key.startswith(prefix):
            continue
        rest = key[len(prefix) :].lower()
        for section_name in ("general", "magisk", "tools"):
            if rest.startswith(section_name + "_"):
                field_name = rest[len(section_name) + 1 :]
                _apply(getattr(cfg, section_name), {field_name: value}, section_name)
                break
    return cfg


def write_default(path: Path | None = None) -> Path:
    path = path or default_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    cfg = Config()
    lines = ["# sudroid configuration", ""]
    for section_name in ("general", "magisk", "tools"):
        lines.append(f"[{section_name}]")
        for f in fields(getattr(cfg, section_name)):
            v = getattr(getattr(cfg, section_name), f.name)
            if isinstance(v, bool):
                lines.append(f"{f.name} = {'true' if v else 'false'}")
            elif isinstance(v, int):
                lines.append(f"{f.name} = {v}")
            else:
                lines.append(f'{f.name} = "{v}"')
        lines.append("")
    path.write_text("\n".join(lines))
    return path
