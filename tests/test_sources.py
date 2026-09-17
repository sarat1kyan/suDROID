import io
import zipfile
from pathlib import Path

import pytest

from sudroid.errors import PreconditionError
from sudroid.images.sources import extract_firmware, kind_of
from tests.payload_builder import PayloadBuilder, padded


def factory_zip(tmp_path: Path, nested: bool = True) -> Path:
    inner = io.BytesIO()
    with zipfile.ZipFile(inner, "w") as izf:
        izf.writestr("boot.img", b"ANDROID!" + b"\x01" * 100)
        izf.writestr("init_boot.img", b"ANDROID!" + b"\x02" * 100)
        izf.writestr("vbmeta.img", b"AVB0" + b"\x00" * 100)
        izf.writestr("system.img", b"S" * 100)
    p = tmp_path / "panther-up1a.231105.003-factory-1234abcd.zip"
    with zipfile.ZipFile(p, "w") as zf:
        if nested:
            zf.writestr(
                "panther-up1a.231105.003/image-panther-up1a.231105.003.zip", inner.getvalue()
            )
            zf.writestr("panther-up1a.231105.003/bootloader-panther-x.img", b"BL")
            zf.writestr("panther-up1a.231105.003/flash-all.sh", "#!/bin/sh\n")
        else:
            zf.writestr("boot.img", b"ANDROID!" + b"\x03" * 10)
    return p


def test_kind_detection(tmp_path: Path) -> None:
    assert kind_of(Path("AP_X.tar.md5")) == "samsung-ap"
    assert kind_of(Path("AP_X.tar")) == "samsung-ap"
    assert kind_of(Path("payload.bin")) == "payload"
    assert kind_of(Path("boot.img")) == "image"
    assert kind_of(factory_zip(tmp_path)) == "factory"
    b = PayloadBuilder()
    b.add("boot", b"ANDROID!")
    assert kind_of(b.write_zip(tmp_path / "ota.zip")) == "ota"
    with pytest.raises(PreconditionError):
        kind_of(Path("x.7z"))


def test_extract_factory_nested(tmp_path: Path) -> None:
    out = extract_firmware(factory_zip(tmp_path), ["init_boot", "vbmeta.img"], tmp_path / "o")
    assert set(out) == {"init_boot.img", "vbmeta.img"}
    assert out["init_boot.img"].read_bytes().startswith(b"ANDROID!\x02")


def test_extract_factory_flat(tmp_path: Path) -> None:
    out = extract_firmware(factory_zip(tmp_path, nested=False), ["boot"], tmp_path / "o")
    assert out["boot.img"].read_bytes() == b"ANDROID!" + b"\x03" * 10


def test_extract_ota(tmp_path: Path) -> None:
    b = PayloadBuilder()
    b.add("boot", b"ANDROID!" + b"\x05" * 50, mode="xz")
    z = b.write_zip(tmp_path / "ota.zip")
    out = extract_firmware(z, ["boot"], tmp_path / "o")
    assert out["boot.img"].read_bytes() == padded(b"ANDROID!" + b"\x05" * 50)


def test_extract_raw_image(tmp_path: Path) -> None:
    img = tmp_path / "boot.img"
    img.write_bytes(b"ANDROID!")
    out = extract_firmware(img, ["boot"], tmp_path / "o")
    assert out["boot.img"].read_bytes() == b"ANDROID!"


def test_missing_archive(tmp_path: Path) -> None:
    with pytest.raises(PreconditionError):
        extract_firmware(tmp_path / "nope.zip", ["boot"], tmp_path / "o")
