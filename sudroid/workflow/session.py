"""Checkpointed sessions for resume."""

from __future__ import annotations

import dataclasses
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from sudroid.paths import sessions_dir

log = logging.getLogger(__name__)


@dataclass
class Session:
    id: str
    serial: str
    command: str
    created: str
    steps_done: list[str] = field(default_factory=list)
    data: dict[str, str] = field(default_factory=dict)
    status: str = "running"  # running, failed, done

    def path(self, root: Path | None = None) -> Path:
        return (root or sessions_dir()) / _safe(self.serial) / f"{self.id}.json"


def new_session(serial: str, command: str) -> Session:
    return Session(
        id=time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6],
        serial=serial,
        command=command,
        created=time.strftime("%Y-%m-%dT%H:%M:%S"),
    )


def save(session: Session, root: Path | None = None) -> Path:
    p = session.path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(dataclasses.asdict(session), indent=2))
    tmp.replace(p)
    return p


def load(path: Path) -> Session:
    return Session(**json.loads(path.read_text()))


def list_sessions(serial: str, root: Path | None = None) -> list[Session]:
    d = (root or sessions_dir()) / _safe(serial)
    if not d.is_dir():
        return []
    out: list[Session] = []
    for p in sorted(d.glob("*.json")):
        try:
            out.append(load(p))
        except (json.JSONDecodeError, TypeError):
            log.warning("skipping corrupt session %s", p)
    return out


def latest_incomplete(serial: str, command: str, root: Path | None = None) -> Session | None:
    for s in reversed(list_sessions(serial, root)):
        if s.command == command and s.status != "done":
            return s
    return None


def _safe(serial: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in serial) or "unknown"
