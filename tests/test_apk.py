from pathlib import Path

import pytest

from sudroid.errors import PatchError
from sudroid.root.apk import extract_bundle
from tests.test_releases import fake_apk


def test_extract_arm64_bundle(tmp_path: Path) -> None:
    apk = tmp_path / "m.apk"
    apk.write_bytes(fake_apk())
    b = extract_bundle(apk, "arm64-v8a", tmp_path / "out", version="v28.0")
    assert b.abi == "arm64-v8a" and b.version == "v28.0"
    names = set(b.files)
    assert {
        "boot_patch.sh",
        "util_functions.sh",
        "stub.apk",
        "magiskboot",
        "magiskinit",
        "magisk",
        "init-ld",
        "magisk32",
        "magisk.apk",
    } <= names
    assert (b.dir / "magiskboot").read_bytes() == b"arm64-v8a-magiskboot"
    assert (b.dir / "magisk32").read_bytes() == b"armeabi-v7a-magisk"
    assert b.apk.is_file()


def test_extract_missing_abi(tmp_path: Path) -> None:
    apk = tmp_path / "m.apk"
    apk.write_bytes(fake_apk(abis=("x86_64",)))
    with pytest.raises(PatchError) as ei:
        extract_bundle(apk, "arm64-v8a", tmp_path / "out")
    assert "x86_64" in (ei.value.hint or "")
