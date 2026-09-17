"""Stock image backups with a JSON manifest per device serial."""

from __future__ import annotations

import dataclasses
import json
import logging
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

from sudroid.device.model import Device
from sudroid.images.verify import sha256_file

log = logging.getLogger(__name__)


@dataclass
class BackupEntry:
    id: str
    created: str
    serial: str
    model: str
    codename: str
    build_id: str
    fingerprint: str
    partition: str
    slot: str
    sha256: str
    size: int
    source: str
    path: str

    def file(self) -> Path:
        return Path(self.path)


class BackupManager:
    def __init__(self, root: Path) -> None:
        self.root = root

    def _dir(self, serial: str) -> Path:
        return self.root / _safe(serial)

    def _manifest(self, serial: str) -> Path:
        return self._dir(serial) / "manifest.json"

    def list(self, serial: str) -> list[BackupEntry]:
        m = self._manifest(serial)
        if not m.is_file():
            return []
        try:
            data = json.loads(m.read_text())
        except json.JSONDecodeError:
            log.warning("corrupt manifest %s", m)
            return []
        out: list[BackupEntry] = []
        for item in data.get("backups", []):
            try:
                out.append(BackupEntry(**item))
            except TypeError:
                log.warning("skipping malformed backup entry in %s", m)
        return out

    def has_backup(self, serial: str) -> bool:
        return any(e.file().is_file() for e in self.list(serial))

    def latest(
        self, serial: str, partition: str, build_id: str | None = None
    ) -> BackupEntry | None:
        entries = [
            e
            for e in self.list(serial)
            if e.partition == partition and (build_id is None or e.build_id == build_id)
        ]
        entries = [e for e in entries if e.file().is_file()]
        return entries[-1] if entries else None

    def save(self, device: Device, partition: str, image: Path, source: str) -> BackupEntry:
        d = self._dir(device.serial)
        d.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        bid = f"{stamp}-{partition}"
        dest = d / f"{bid}.img"
        n = 1
        while dest.exists():
            n += 1
            dest = d / f"{bid}-{n}.img"
        shutil.copy2(image, dest)
        entry = BackupEntry(
            id=dest.stem,
            created=time.strftime("%Y-%m-%dT%H:%M:%S"),
            serial=device.serial,
            model=device.model,
            codename=device.codename,
            build_id=device.build_id,
            fingerprint=device.fingerprint,
            partition=partition,
            slot=device.slot,
            sha256=sha256_file(dest),
            size=dest.stat().st_size,
            source=source,
            path=str(dest),
        )
        entries = self.list(device.serial)
        entries.append(entry)
        payload = {
            "version": 1,
            "serial": device.serial,
            "backups": [dataclasses.asdict(e) for e in entries],
        }
        tmp = self._manifest(device.serial).with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2))
        tmp.replace(self._manifest(device.serial))
        log.info("backup saved: %s", dest)
        return entry

    def verify(self, entry: BackupEntry) -> bool:
        f = entry.file()
        return f.is_file() and sha256_file(f) == entry.sha256


def _safe(serial: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in serial) or "unknown"
