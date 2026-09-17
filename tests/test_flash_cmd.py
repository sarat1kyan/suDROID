from pathlib import Path

import pytest
from typer.testing import CliRunner

from sudroid import cli
from tests.flow_helpers import FakeDevice, boot_image, install

runner = CliRunner()


def test_flash_boot_to_current_slot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dev = FakeDevice("oneplus9")
    install(monkeypatch, tmp_path, dev)
    img = tmp_path / "ksu_boot.img"
    img.write_bytes(boot_image())
    r = runner.invoke(cli.app, ["--yes", "flash", str(img), "--partition", "boot"])
    assert r.exit_code == 0, r.output
    assert dev.flashed == [("boot_a", str(img))]
    assert dev.booted == []


def test_flash_explicit_slot_and_test_boot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dev = FakeDevice("oneplus9")
    install(monkeypatch, tmp_path, dev)
    img = tmp_path / "boot.img"
    img.write_bytes(boot_image())
    r = runner.invoke(
        cli.app, ["--yes", "flash", str(img), "--partition", "boot", "--slot", "b", "--test-boot"]
    )
    assert r.exit_code == 0, r.output
    assert dev.booted == [str(img)]
    assert dev.flashed == [("boot_b", str(img))]


def test_flash_refuses_wrong_kind(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dev = FakeDevice("oneplus9")
    install(monkeypatch, tmp_path, dev)
    img = tmp_path / "x.img"
    img.write_bytes(b"junk" * 100)
    r = runner.invoke(cli.app, ["--yes", "flash", str(img), "--partition", "boot"])
    assert r.exit_code == 50
    assert "refusing" in r.output
    assert dev.flashed == []


def test_flash_refuses_kernel_in_init_boot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dev = FakeDevice("pixel7", byname="boot_a init_boot_a")
    install(monkeypatch, tmp_path, dev)
    img = tmp_path / "boot.img"
    img.write_bytes(boot_image(kernel=500, version=4))
    r = runner.invoke(cli.app, ["--yes", "flash", str(img), "--partition", "init_boot"])
    assert r.exit_code == 50
    assert "kernel" in r.output


def test_flash_missing_partition(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dev = FakeDevice("oneplus9")
    install(monkeypatch, tmp_path, dev)
    img = tmp_path / "vb.img"
    img.write_bytes(boot_image(kernel=0, version=4))
    r = runner.invoke(cli.app, ["--yes", "flash", str(img), "--partition", "init_boot"])
    assert r.exit_code == 50
    assert "not present" in r.output


def test_backup_and_restore(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dev = FakeDevice("oneplus9")
    install(monkeypatch, tmp_path, dev)
    img = tmp_path / "boot.img"
    img.write_bytes(boot_image())
    r = runner.invoke(cli.app, ["--yes", "backup", "--image", str(img)])
    assert r.exit_code == 0, r.output
    r = runner.invoke(cli.app, ["--json", "backup", "--list"])
    assert r.exit_code == 0, r.output
    assert '"partition": "boot"' in r.stdout
    r = runner.invoke(cli.app, ["--yes", "restore"])
    assert r.exit_code == 0, r.output
    assert len(dev.flashed) == 1 and dev.flashed[0][0] == "boot_a"


def test_restore_without_backup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dev = FakeDevice("oneplus9")
    install(monkeypatch, tmp_path, dev)
    r = runner.invoke(cli.app, ["--yes", "restore"])
    assert r.exit_code == 20
    assert "no backup" in r.output


def test_patch_command_only_patches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dev = FakeDevice("oneplus9")
    install(monkeypatch, tmp_path, dev)
    img = tmp_path / "boot.img"
    img.write_bytes(boot_image())
    out = tmp_path / "out.img"
    r = runner.invoke(cli.app, ["--yes", "patch", str(img), "--out", str(out)])
    assert r.exit_code == 0, r.output
    assert out.is_file()
    assert dev.flashed == [] and dev.booted == []


def test_verify_reports(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dev = FakeDevice("oneplus9")
    dev.rooted = True
    install(monkeypatch, tmp_path, dev)
    r = runner.invoke(cli.app, ["verify"])
    assert r.exit_code == 0, r.output
    assert "rooted" in r.output and "28.0" in r.output


def test_samsung_root_blocked_this_release(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dev = FakeDevice("s23", byname="boot init_boot vbmeta")
    install(monkeypatch, tmp_path, dev)
    r = runner.invoke(cli.app, ["--yes", "root", "--image", "x.img"])
    assert r.exit_code == 20
    assert "heimdall" in r.output
