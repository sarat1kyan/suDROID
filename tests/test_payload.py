from pathlib import Path

import pytest

from sudroid.images.payload import (
    PayloadError,
    extract,
    extract_from_file,
    extract_from_zip,
    open_payload,
)
from tests.payload_builder import PayloadBuilder, as_io, padded

BOOT = (
    b"ANDROID!" + bytes(range(256)) * 40 + b"\x00" * 9000
)  # trailing zeros -> ZERO op in auto mode
VBMETA = b"AVB0" + b"\x11" * 300


def test_open_and_extract_replace_and_zero(tmp_path: Path) -> None:
    b = PayloadBuilder()
    b.add("boot", BOOT, mode="auto", ops_split=4)
    b.add("vbmeta", VBMETA, mode="xz")
    b.add("system", b"S" * 10000, mode="bz")
    p = open_payload(as_io(b.build()))
    assert p.block_size == 4096
    assert set(p.names()) == {"boot", "vbmeta", "system"}
    assert any(op.type == 6 for op in p.partitions["boot"].ops)
    out = extract(p, "boot", tmp_path / "boot.img")
    assert out.read_bytes() == padded(BOOT)
    assert extract(p, "vbmeta", tmp_path / "vb.img").read_bytes() == padded(VBMETA)
    assert extract(p, "system", tmp_path / "s.img").read_bytes() == padded(b"S" * 10000)


def test_missing_partition_lists_available(tmp_path: Path) -> None:
    b = PayloadBuilder()
    b.add("boot", BOOT)
    p = open_payload(as_io(b.build()))
    with pytest.raises(PayloadError) as ei:
        extract(p, "init_boot", tmp_path / "x")
    assert "boot" in (ei.value.hint or "")


def test_incremental_rejected(tmp_path: Path) -> None:
    b = PayloadBuilder()
    b.add("boot", BOOT, op_type_override=3)  # BSDIFF
    p = open_payload(as_io(b.build()))
    with pytest.raises(PayloadError) as ei:
        extract(p, "boot", tmp_path / "x")
    assert "BSDIFF" in ei.value.message


def test_bad_magic_and_version() -> None:
    with pytest.raises(PayloadError):
        open_payload(as_io(b"NOPE" + b"\x00" * 40))
    b = PayloadBuilder()
    b.add("boot", BOOT)
    raw = bytearray(b.build())
    raw[4:12] = (1).to_bytes(8, "big")
    with pytest.raises(PayloadError):
        open_payload(as_io(bytes(raw)))


def test_hash_mismatch_detected(tmp_path: Path) -> None:
    b = PayloadBuilder()
    b.add("boot", BOOT)
    raw = bytearray(b.build())
    raw[-1] ^= 0xFF  # corrupt last data byte
    p = open_payload(as_io(bytes(raw)))
    with pytest.raises(PayloadError):
        extract(p, "boot", tmp_path / "boot.img")


def test_extract_from_zip_and_file(tmp_path: Path) -> None:
    b = PayloadBuilder()
    b.add("boot", BOOT)
    b.add("init_boot", b"ANDROID!" + b"\x02" * 100)
    z = b.write_zip(tmp_path / "ota.zip")
    out = extract_from_zip(z, ["init_boot.img", "vbmeta.img"], tmp_path / "o")
    assert set(out) == {"init_boot.img"}
    raw = tmp_path / "payload.bin"
    raw.write_bytes(b.build())
    out2 = extract_from_file(raw, ["boot"], tmp_path / "o2")
    assert out2["boot.img"].read_bytes() == padded(BOOT)
    with pytest.raises(PayloadError):
        extract_from_zip(z, ["vendor_boot.img"], tmp_path / "o3")


def test_extract_from_deflated_zip(tmp_path: Path) -> None:
    import zipfile

    b = PayloadBuilder()
    b.add("boot", BOOT)
    z = tmp_path / "ota_deflated.zip"
    with zipfile.ZipFile(z, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("payload.bin", b.build())
    out = extract_from_zip(z, ["boot"], tmp_path / "o")
    assert out["boot.img"].read_bytes() == padded(BOOT)
    assert not (tmp_path / "o" / "payload.bin").exists()


def test_oversized_op_rejected(tmp_path: Path) -> None:
    from sudroid.images import payload as pl

    b = PayloadBuilder()
    b.add("boot", BOOT)
    p = open_payload(as_io(b.build()))
    op = p.partitions["boot"].ops[0]
    p.partitions["boot"].ops[0] = pl.Operation(
        op.type, op.data_offset, pl.MAX_OP_DATA + 1, op.dst_extents, op.sha256
    )
    with pytest.raises(PayloadError):
        extract(p, "boot", tmp_path / "x.img")
