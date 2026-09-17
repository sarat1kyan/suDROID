from pathlib import Path

from sudroid.backup.manager import BackupManager
from sudroid.device.detect import detect
from sudroid.device.model import RawInfo
from sudroid.device.props import Props
from tests.conftest import getprop_text


def dev(name: str = "pixel5"):  # type: ignore[no-untyped-def]
    return detect(RawInfo(props=Props.parse(getprop_text(name))))


def test_save_list_latest_verify(tmp_path: Path) -> None:
    img = tmp_path / "boot.img"
    img.write_bytes(b"A" * 1000)
    bm = BackupManager(tmp_path / "backups")
    d = dev()
    assert not bm.has_backup(d.serial)
    e1 = bm.save(d, "boot", img, "user-file")
    assert bm.has_backup(d.serial)
    assert e1.partition == "boot" and e1.slot == "b" and e1.build_id == d.build_id
    assert Path(e1.path).is_file() and e1.size == 1000
    img.write_bytes(b"B" * 500)
    e2 = bm.save(d, "boot", img, "rooted-dd")
    assert e2.id != e1.id
    assert bm.latest(d.serial, "boot") == e2
    assert bm.latest(d.serial, "boot", build_id="nope") is None
    assert bm.latest(d.serial, "init_boot") is None
    assert bm.verify(e1) and bm.verify(e2)
    Path(e2.path).write_bytes(b"corrupt")
    assert not bm.verify(e2)


def test_missing_file_ignored_in_latest(tmp_path: Path) -> None:
    img = tmp_path / "boot.img"
    img.write_bytes(b"A")
    bm = BackupManager(tmp_path / "b")
    d = dev()
    e = bm.save(d, "boot", img, "x")
    Path(e.path).unlink()
    assert bm.latest(d.serial, "boot") is None
    assert not bm.has_backup(d.serial)


def test_corrupt_manifest(tmp_path: Path) -> None:
    bm = BackupManager(tmp_path)
    (tmp_path / "S").mkdir()
    (tmp_path / "S" / "manifest.json").write_text("{bad")
    assert bm.list("S") == []
