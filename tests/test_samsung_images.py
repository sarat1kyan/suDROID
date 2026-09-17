import hashlib
import io
import tarfile
from pathlib import Path

import lz4.frame
import pytest

from sudroid.errors import PreconditionError
from sudroid.images.samsung import build_odin_tar, extract_ap, list_ap


def make_ap(tmp_path: Path, *, md5: bool = True, raw_vbmeta: bool = False) -> Path:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tf:

        def add(name: str, data: bytes) -> None:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))

        add("boot.img.lz4", lz4.frame.compress(b"ANDROID!" + b"\x00" * 100))
        add("init_boot.img.lz4", lz4.frame.compress(b"ANDROID!" + b"\x01" * 50))
        vb = b"AVB0" + b"\x00" * 252
        add(
            "vbmeta.img" if raw_vbmeta else "vbmeta.img.lz4",
            vb if raw_vbmeta else lz4.frame.compress(vb),
        )
        add("userdata.img.lz4", lz4.frame.compress(b"U" * 10))
        add("meta-data/fota.zip", b"zip")
    data = buf.getvalue()
    p = tmp_path / ("AP_test.tar.md5" if md5 else "AP_test.tar")
    if md5:
        data += (hashlib.md5(data).hexdigest() + "  AP_test.tar\n").encode()
    p.write_bytes(data)
    return p


def test_list_and_extract_lz4(tmp_path: Path) -> None:
    ap = make_ap(tmp_path)
    assert "boot.img.lz4" in list_ap(ap)
    out = extract_ap(ap, tmp_path / "out")
    assert set(out) == {"boot.img", "init_boot.img", "vbmeta.img"}
    assert out["boot.img"].read_bytes().startswith(b"ANDROID!")
    assert out["vbmeta.img"].read_bytes()[:4] == b"AVB0"
    assert not (tmp_path / "out" / "userdata.img").exists()


def test_extract_raw_entries_and_plain_tar(tmp_path: Path) -> None:
    ap = make_ap(tmp_path, md5=False, raw_vbmeta=True)
    out = extract_ap(ap, tmp_path / "o")
    assert out["vbmeta.img"].stat().st_size == 256


def test_extract_nothing_found(tmp_path: Path) -> None:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tf:
        info = tarfile.TarInfo("system.img.lz4")
        info.size = 1
        tf.addfile(info, io.BytesIO(b"x"))
    p = tmp_path / "AP.tar"
    p.write_bytes(buf.getvalue())
    with pytest.raises(PreconditionError):
        extract_ap(p, tmp_path / "o")


def test_not_a_tar(tmp_path: Path) -> None:
    p = tmp_path / "x.tar.md5"
    p.write_bytes(b"garbage")
    with pytest.raises(PreconditionError):
        list_ap(p)


def test_build_odin_tar_md5_trailer(tmp_path: Path) -> None:
    b = tmp_path / "boot.img"
    b.write_bytes(b"B" * 3000)
    v = tmp_path / "vbmeta.img"
    v.write_bytes(b"V" * 256)
    out = build_odin_tar({"boot.img": b, "vbmeta.img": v}, tmp_path / "magisk_patched.tar")
    assert out.name == "magisk_patched.tar.md5"
    data = out.read_bytes()
    trailer_len = 32 + 2 + len("magisk_patched.tar") + 1
    trailer = data[-trailer_len:].rstrip(b"\n")
    digest, _, name = trailer.decode().partition("  ")
    tar_bytes = data[:-trailer_len]
    assert hashlib.md5(tar_bytes).hexdigest() == digest
    assert name == "magisk_patched.tar"
    with tarfile.open(fileobj=io.BytesIO(tar_bytes)) as tf:
        names = tf.getnames()
        assert names == ["boot.img", "vbmeta.img"]
        m = tf.getmember("boot.img")
        assert m.size == 3000 and m.mode == 0o644
    # Python can still open the .tar.md5 directly
    with tarfile.open(out) as tf:
        assert tf.getnames() == ["boot.img", "vbmeta.img"]
