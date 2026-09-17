import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from sudroid import cli
from sudroid.tools import platform_tools
from sudroid.tools.base import FakeRunner
from tests.conftest import getprop_text

runner = CliRunner()


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> FakeRunner:
    fk = FakeRunner()
    monkeypatch.setattr(cli, "_make_runner", lambda: fk)
    monkeypatch.setattr(platform_tools, "ensure", lambda name, **kw: Path(f"/fake/{name}"))
    monkeypatch.setenv("SUDROID_GENERAL_LOG_LEVEL", "warning")
    monkeypatch.setattr(cli.config_mod, "default_path", lambda: tmp_path / "none.toml")
    return fk


def _device(fk: FakeRunner, name: str, serial: str = "ABC", byname: str = "boot_a boot_b") -> None:
    fk.on(("/fake/adb", "devices"), f"List of devices attached\n{serial}\tdevice\n")
    fk.on(("/fake/adb", "-s", serial, "shell", "getprop"), getprop_text(name))
    fk.on_prefix(("/fake/adb", "-s", serial, "shell", "ls /dev/block/by-name"), byname)
    fk.on_prefix(("/fake/adb", "-s", serial, "shell", "command -v"), "no")
    fk.on(("/fake/adb", "-s", serial, "shell", "dumpsys battery"), "  level: 64\n")


def test_version() -> None:
    r = runner.invoke(cli.app, ["--version"])
    assert r.exit_code == 0
    assert r.stdout.strip().startswith("3.")


def test_profiles_lists_all(fake: FakeRunner) -> None:
    r = runner.invoke(cli.app, ["profiles"])
    assert r.exit_code == 0, r.output
    for name in (
        "Google Pixel",
        "Samsung Galaxy",
        "Xiaomi",
        "OnePlus",
        "Motorola",
        "Sony",
        "ASUS",
        "Nothing",
        "Generic",
    ):
        assert name in r.output


def test_profiles_json(fake: FakeRunner) -> None:
    r = runner.invoke(cli.app, ["--json", "profiles"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.stdout)
    assert len(data) == 9
    assert any(p["vendor"] == "samsung" and p["flash_backend"] == "heimdall" for p in data)


def test_info_json_pixel7(fake: FakeRunner) -> None:
    _device(fake, "pixel7", byname="boot_a boot_b init_boot_a init_boot_b")
    r = runner.invoke(cli.app, ["--json", "info"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.stdout)
    assert data["vendor"] == "google"
    assert data["effective_patch_target"] == "init_boot"
    assert data["battery"] == 64
    assert data["profile"] == "Google Pixel"


def test_info_human_s23(fake: FakeRunner) -> None:
    _device(fake, "s23")
    r = runner.invoke(cli.app, ["info"])
    assert r.exit_code == 0, r.output
    assert "Samsung Galaxy" in r.output
    assert "heimdall" in r.output
    assert "Knox" in r.output
    assert "sudroid unlock" in r.output


def test_info_no_device_exit_10(fake: FakeRunner) -> None:
    fake.on(("/fake/adb", "devices"), "List of devices attached\n\n")
    r = runner.invoke(cli.app, ["info"])
    assert r.exit_code == 10
    assert "no device" in r.output


def test_info_multiple_devices_exit_11(fake: FakeRunner) -> None:
    fake.on(("/fake/adb", "devices"), "List of devices attached\nA\tdevice\nB\tdevice\n")
    r = runner.invoke(cli.app, ["info"])
    assert r.exit_code == 11
    assert "--serial" in r.output


def test_info_serial_selects(fake: FakeRunner) -> None:
    _device(fake, "pixel5", serial="B")
    fake.on(("/fake/adb", "devices"), "List of devices attached\nA\tdevice\nB\tdevice\n")
    r = runner.invoke(cli.app, ["--json", "--serial", "B", "info"])
    assert r.exit_code == 0, r.output
    assert json.loads(r.stdout)["model"] == "Pixel 5"


def test_info_unauthorized_exit_20(fake: FakeRunner) -> None:
    fake.on(("/fake/adb", "devices"), "List of devices attached\nA\tunauthorized\n")
    r = runner.invoke(cli.app, ["info"])
    assert r.exit_code == 20
    assert "unauthorized" in r.output


def test_doctor_ok(fake: FakeRunner) -> None:
    fake.on(("/fake/adb", "start-server"), "")
    fake.on(("/fake/adb", "devices"), "List of devices attached\nA\tdevice\n")
    r = runner.invoke(cli.app, ["doctor"])
    assert r.exit_code == 0, r.output
    assert "adb" in r.output and "fastboot" in r.output


def test_doctor_missing_adb_exit_12(fake: FakeRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    from sudroid.errors import ToolMissingError

    def ensure(name: str, **kw: object) -> Path:
        if name == "adb":
            raise ToolMissingError("adb not found", hint="install it")
        return Path(f"/fake/{name}")

    monkeypatch.setattr(platform_tools, "ensure", ensure)
    r = runner.invoke(cli.app, ["doctor"])
    assert r.exit_code == 12
    assert "install it" in r.output


def test_dry_run_banner(fake: FakeRunner) -> None:
    r = runner.invoke(cli.app, ["--dry-run", "profiles"])
    assert r.exit_code == 0
    assert "dry-run" in r.output


def test_config_show(fake: FakeRunner) -> None:
    r = runner.invoke(cli.app, ["config"])
    assert r.exit_code == 0, r.output
    assert "min_battery" in r.output
