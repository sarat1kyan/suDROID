from pathlib import Path

import pytest
from typer.testing import CliRunner

from sudroid import cli
from sudroid.commands import unlock as unlock_mod
from sudroid.tools.base import Result
from sudroid.ui import prompts
from tests.flow_helpers import FakeDevice, boot_image, install

runner = CliRunner()


def add_unlock_handlers(dev: FakeDevice, *, unlocked_after: bool = True) -> None:
    fk = dev.runner
    state = {"unlocked": False}

    def unlock(a: tuple[str, ...]) -> Result:
        state["unlocked"] = unlocked_after
        return Result(a, 0, "", "OKAY\n", 0.0)

    fk.on(("fastboot", "flashing", "unlock"), unlock)
    fk.on_prefix(("fastboot", "oem", "unlock"), unlock)
    fk.on(
        ("fastboot", "oem", "get_unlock_data"),
        lambda a: Result(
            a,
            0,
            "",
            "(bootloader) 0A40040192024205#4C4D3556313230\n"
            "(bootloader) 30373731363031303332323239#BD00\nOKAY\n",
            0.0,
        ),
    )
    fk.on(
        ("fastboot", "getvar", "unlocked"),
        lambda a: Result(
            a, 0, "", f"unlocked: {'yes' if state['unlocked'] else 'no'}\nFinished.\n", 0.0
        ),
    )


def with_backup(tmp_path: Path) -> None:
    img = tmp_path / "boot.img"
    img.write_bytes(boot_image())
    r = runner.invoke(cli.app, ["--yes", "backup", "--image", str(img)])
    assert r.exit_code == 0, r.output


def test_pixel_unlock_flashing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dev = FakeDevice("pixel5")
    # pixel5 fixture has OEM unlocking off; flip it for this test
    dev.runner.responses[("adb", "-s", "S", "shell", "getprop")] = dev.runner.responses[
        ("adb", "-s", "S", "shell", "getprop")
    ].replace(  # type: ignore[union-attr]
        "[sys.oem_unlock_allowed]: [0]", "[sys.oem_unlock_allowed]: [1]"
    )
    install(monkeypatch, tmp_path, dev)
    add_unlock_handlers(dev)
    with_backup(tmp_path)
    monkeypatch.setattr(prompts.Prompt, "ask", staticmethod(lambda *a, **k: "UNLOCK"))
    r = runner.invoke(cli.app, ["unlock"])
    assert r.exit_code == 0, r.output
    assert ("fastboot", "flashing", "unlock") in dev.runner.mutating_calls
    assert ("fastboot", "reboot") in dev.runner.mutating_calls
    assert "unlock issued" in r.output


def test_unlock_requires_backup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dev = FakeDevice("oneplus9")
    dev.runner.responses[("adb", "-s", "S", "shell", "getprop")] = dev.runner.responses[
        ("adb", "-s", "S", "shell", "getprop")
    ].replace(  # type: ignore[union-attr]
        "[ro.boot.verifiedbootstate]: [orange]", "[ro.boot.verifiedbootstate]: [green]"
    )
    install(monkeypatch, tmp_path, dev)
    r = runner.invoke(cli.app, ["unlock"])
    assert r.exit_code == 20, r.output
    assert "sudroid backup" in r.output
    assert dev.runner.mutating_calls == []


def test_unlock_wrong_word_aborts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dev = FakeDevice("motog")
    install(monkeypatch, tmp_path, dev)
    add_unlock_handlers(dev)
    monkeypatch.setattr(prompts.Prompt, "ask", staticmethod(lambda *a, **k: "unlock"))
    r = runner.invoke(cli.app, ["unlock", "--i-know"])
    assert r.exit_code == 30
    assert dev.runner.mutating_calls == []


def test_motorola_unlock_data_then_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dev = FakeDevice("motog")
    install(monkeypatch, tmp_path, dev)
    add_unlock_handlers(dev)
    answers = iter(["UNLOCK", "ABCDEF0123456789ABCD"])
    monkeypatch.setattr(prompts.Prompt, "ask", staticmethod(lambda *a, **k: next(answers)))
    monkeypatch.setattr(unlock_mod.Prompt, "ask", staticmethod(lambda *a, **k: next(answers)))
    r = runner.invoke(cli.app, ["unlock", "--i-know"])
    assert r.exit_code == 0, r.output
    assert "0A40040192024205#4C4D355631323030373731363031303332323239#BD00" in r.output
    assert ("fastboot", "oem", "unlock", "ABCDEF0123456789ABCD") in dev.runner.mutating_calls
    assert ("fastboot", "oem", "get_unlock_data") not in dev.runner.mutating_calls


def test_xiaomi_guided_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dev = FakeDevice("mi11")
    install(monkeypatch, tmp_path, dev)
    r = runner.invoke(cli.app, ["unlock", "--i-know"])
    assert r.exit_code == 20, r.output  # OEM unlocking off in fixture
    assert "Mi Unlock" in r.output
    assert dev.runner.mutating_calls == []


def test_already_unlocked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dev = FakeDevice("oneplus9")
    install(monkeypatch, tmp_path, dev)
    r = runner.invoke(cli.app, ["unlock"])
    assert r.exit_code == 0
    assert "already unlocked" in r.output


def test_samsung_us_variant_blocked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dev = FakeDevice("s23")
    dev.runner.responses[("adb", "-s", "S", "shell", "getprop")] = dev.runner.responses[
        ("adb", "-s", "S", "shell", "getprop")
    ].replace(  # type: ignore[union-attr]
        "[ro.product.model]: [SM-S911B]", "[ro.product.model]: [SM-S911U]"
    )
    install(monkeypatch, tmp_path, dev)
    r = runner.invoke(cli.app, ["unlock"])
    assert r.exit_code == 20
    assert "US variant" in r.output
