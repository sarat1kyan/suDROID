from pathlib import Path

import pytest
from typer.testing import CliRunner

from sudroid import cli
from tests.flow_helpers import FakeDevice, boot_image, install

runner = CliRunner()


def mutating_device_ops(dev: FakeDevice) -> list[tuple[str, ...]]:
    out = []
    for c in dev.runner.mutating_calls:
        if (
            c[0] == "fastboot"
            or c[-2:] == ("reboot", "bootloader")
            or (len(c) > 3 and c[3] == "install")
        ):
            out.append(c)
    return out


def test_root_oneplus9_boot_target_with_test_boot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dev = FakeDevice("oneplus9")
    install(monkeypatch, tmp_path, dev)
    stock = tmp_path / "boot.img"
    stock.write_bytes(boot_image())
    r = runner.invoke(cli.app, ["--yes", "root", "--image", str(stock)])
    assert r.exit_code == 0, r.output
    ops = mutating_device_ops(dev)
    assert ops[0] == ("adb", "-s", "S", "reboot", "bootloader")
    assert ops[1][:2] == ("fastboot", "boot")
    assert ops[2] == ("adb", "-s", "S", "reboot", "bootloader")
    assert ops[3][:3] == ("fastboot", "flash", "boot_a")
    assert ops[4] == ("fastboot", "reboot")
    assert ops[5][3:5] == ("install", "-r")
    assert dev.flashed == [("boot_a", dev.flashed[0][1])]
    assert dev.flashed[0][1].endswith("patched_boot.img")
    assert "root verified" in r.output
    assert (tmp_path / "backups" / "a1b2c3d4" / "manifest.json").is_file()


def test_root_pixel7_init_boot_skips_test_boot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dev = FakeDevice("pixel7", byname="boot_a boot_b init_boot_a init_boot_b vbmeta_a")
    install(monkeypatch, tmp_path, dev)
    stock = tmp_path / "init_boot.img"
    stock.write_bytes(boot_image(kernel=0, version=4))
    r = runner.invoke(cli.app, ["--yes", "root", "--image", str(stock)])
    assert r.exit_code == 0, r.output
    assert dev.booted == []
    assert [p for p, _ in dev.flashed] == ["init_boot_a"]
    assert "cannot be test-booted" in r.output


def test_root_refuses_inferred_init_boot_missing_partition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # byname unreadable -> init_boot inferred from API 33; fastboot says partition missing
    dev = FakeDevice("pixel7", byname="")
    dev.partitions = {"boot_a", "boot_b"}
    install(monkeypatch, tmp_path, dev)
    stock = tmp_path / "init_boot.img"
    stock.write_bytes(boot_image(kernel=0, version=4))
    r = runner.invoke(cli.app, ["--yes", "root", "--image", str(stock)])
    assert r.exit_code == 50, r.output
    assert dev.flashed == []
    assert "init_boot_a not present" in r.output


def test_root_locked_exit_20(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dev = FakeDevice("pixel5")
    install(monkeypatch, tmp_path, dev)
    r = runner.invoke(cli.app, ["--yes", "root", "--image", "x.img"])
    assert r.exit_code == 20, r.output
    assert "sudroid unlock" in r.output
    assert dev.runner.mutating_calls == []


def test_root_low_battery_exit_20(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dev = FakeDevice("oneplus9", battery=20)
    install(monkeypatch, tmp_path, dev)
    r = runner.invoke(cli.app, ["--yes", "root", "--image", "x.img"])
    assert r.exit_code == 20, r.output
    assert "battery 20%" in r.output


def test_root_test_boot_without_root_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dev = FakeDevice("oneplus9", rooted_after_boot=False)
    install(monkeypatch, tmp_path, dev)
    stock = tmp_path / "boot.img"
    stock.write_bytes(boot_image())
    r = runner.invoke(cli.app, ["--yes", "root", "--image", str(stock)])
    assert r.exit_code == 20, r.output
    assert dev.booted and dev.flashed == []
    assert "nothing was written" in r.output


def test_root_dry_run_no_device_writes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dev = FakeDevice("oneplus9")
    install(monkeypatch, tmp_path, dev)
    stock = tmp_path / "boot.img"
    stock.write_bytes(boot_image())
    r = runner.invoke(cli.app, ["--dry-run", "root", "--image", str(stock)])
    assert r.exit_code == 0, r.output
    assert dev.runner.mutating_calls == []
    assert dev.flashed == [] and dev.booted == []
    assert "Plan" in r.output


def test_root_resume_skips_done_steps(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dev = FakeDevice("oneplus9")
    install(monkeypatch, tmp_path, dev)
    from sudroid.workflow import session as sm

    s = sm.new_session("a1b2c3d4", "root")
    s.status = "failed"
    s.steps_done = [
        "check_tools",
        "check_backend",
        "check_battery",
        "check_unlocked",
        "acquire_image",
        "backup_stock",
        "fetch_magisk",
        "patch_image",
        "test_boot",
    ]
    patched = tmp_path / "patched_boot.img"
    patched.write_bytes(boot_image(ramdisk=99))
    apk = tmp_path / "m.apk"
    apk.write_bytes(b"apk")
    s.data = {"patched": str(patched), "stock": str(patched), "apk": str(apk)}
    sm.save(s, tmp_path / "sessions")
    r = runner.invoke(cli.app, ["--yes", "root", "--resume"])
    assert r.exit_code == 0, r.output
    assert dev.booted == []
    assert [p for p, _ in dev.flashed] == ["boot_a"]
    assert "resuming session" in r.output


def test_root_apatch_method_redirects(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dev = FakeDevice("oneplus9")
    install(monkeypatch, tmp_path, dev)
    r = runner.invoke(cli.app, ["root", "--method", "apatch"])
    assert r.exit_code == 20
    assert "sudroid flash" in r.output
