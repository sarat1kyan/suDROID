import io
import tarfile
from pathlib import Path

import lz4.frame
import pytest
from typer.testing import CliRunner

from sudroid import cli
from sudroid.tools.base import Result
from tests.flow_helpers import FakeDevice, boot_image, install

runner = CliRunner()


def make_ap(tmp_path: Path) -> Path:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tf:

        def add(name: str, data: bytes) -> None:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))

        add("boot.img.lz4", lz4.frame.compress(boot_image(kernel=500, version=4)))
        add("init_boot.img.lz4", lz4.frame.compress(boot_image(kernel=0, version=4)))
        add("vbmeta.img.lz4", lz4.frame.compress(b"AVB0" + b"\x00" * 4092))
    p = tmp_path / "AP_S911B.tar.md5"
    p.write_bytes(buf.getvalue())
    return p


def samsung_device(unlocked: bool = True) -> FakeDevice:
    dev = FakeDevice("s23", byname="boot init_boot vbmeta recovery")
    key = ("adb", "-s", "S", "shell", "getprop")
    props = dev.runner.responses[key]
    assert isinstance(props, str)
    if unlocked:
        props = props.replace(
            "[ro.boot.verifiedbootstate]: [green]", "[ro.boot.verifiedbootstate]: [orange]"
        )
        props = props.replace("[ro.boot.flash.locked]: [1]", "[ro.boot.flash.locked]: [0]")
    dev.runner.responses[key] = props
    fk = dev.runner
    fk.on(
        ("adb", "-s", "S", "reboot", "download"),
        lambda a: (setattr(dev, "mode", "download"), Result(a, 0, "", "", 0.0))[1],
    )
    fk.on(
        ("heimdall", "detect"), lambda a: Result(a, 0 if dev.mode == "download" else 1, "", "", 0.0)
    )
    fk.on(
        ("heimdall", "print-pit", "--no-reboot"),
        "Partition Name: BOOT\nPartition Name: INIT_BOOT\n"
        "Partition Name: VBMETA\nPartition Name: RECOVERY\n",
    )

    def flash(a: tuple[str, ...]) -> Result:
        pairs = list(zip(a[2::2], a[3::2], strict=True))
        dev.flashed.extend((p.lstrip("-"), v) for p, v in pairs)
        dev.mode = "android"
        dev.rooted = True
        return Result(a, 0, "Upload successful", "", 0.0)

    fk.on_prefix(("heimdall", "flash"), flash)
    return dev


def test_samsung_root_heimdall(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dev = samsung_device()
    install(monkeypatch, tmp_path, dev)
    ap = make_ap(tmp_path)
    r = runner.invoke(cli.app, ["--yes", "root", "--firmware", str(ap)])
    assert r.exit_code == 0, r.output
    parts = dict(dev.flashed)
    assert set(parts) == {"INIT_BOOT", "VBMETA"}
    assert parts["INIT_BOOT"].endswith("patched_init_boot.img")
    assert parts["VBMETA"].endswith("patched_vbmeta.img")
    assert Path(parts["VBMETA"]).read_bytes()[0x78:0x7C] == b"\x00\x00\x00\x03"
    assert dev.booted == []
    assert ("adb", "-s", "S", "reboot", "download") in dev.runner.mutating_calls
    assert "root verified" in r.output
    manifest = tmp_path / "backups" / "R5CW1234ABC" / "manifest.json"
    assert manifest.is_file()
    assert '"partition": "vbmeta"' in manifest.read_text()


def test_samsung_root_odin_tar(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dev = samsung_device()
    install(monkeypatch, tmp_path, dev)
    ap = make_ap(tmp_path)
    r = runner.invoke(cli.app, ["--yes", "root", "--firmware", str(ap), "--odin"])
    assert r.exit_code == 0, r.output
    assert dev.flashed == []
    assert "magisk_patched.tar.md5" in r.output
    assert "Click AP" in r.output
    tar = next((tmp_path / "data" / "work").rglob("magisk_patched.tar.md5"))
    with tarfile.open(tar) as tf:
        assert sorted(tf.getnames()) == ["init_boot.img", "vbmeta.img"]


def test_samsung_needs_firmware(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dev = samsung_device()
    install(monkeypatch, tmp_path, dev)
    r = runner.invoke(cli.app, ["--yes", "root"])
    assert r.exit_code == 20, r.output
    assert "--image" in r.output


def test_samsung_locked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dev = samsung_device(unlocked=False)
    install(monkeypatch, tmp_path, dev)
    r = runner.invoke(cli.app, ["--yes", "root", "--firmware", str(make_ap(tmp_path))])
    assert r.exit_code == 20
    assert "sudroid unlock" in r.output


def test_samsung_missing_heimdall_hint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from sudroid.errors import ToolMissingError
    from sudroid.tools import platform_tools

    dev = samsung_device()
    install(monkeypatch, tmp_path, dev)

    def ensure(name: str, **kw: object) -> Path:
        if name == "heimdall":
            raise ToolMissingError("heimdall not found", hint="Install Heimdall.")
        return Path(name)

    monkeypatch.setattr(platform_tools, "ensure", ensure)
    r = runner.invoke(cli.app, ["--yes", "root", "--firmware", str(make_ap(tmp_path))])
    assert r.exit_code == 20
    assert "--odin" in r.output


def test_fastboot_vendor_bad_firmware(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dev = FakeDevice("oneplus9")
    install(monkeypatch, tmp_path, dev)
    fw = tmp_path / "ota.zip"
    fw.write_bytes(b"PK")
    r = runner.invoke(cli.app, ["--yes", "root", "--firmware", str(fw)])
    assert r.exit_code == 20
    assert "not a valid zip" in r.output
