"""Minimal reader for Android OTA payload.bin (update_engine format).

Only full OTAs are supported: REPLACE, REPLACE_BZ, REPLACE_XZ and ZERO
operations. The manifest is decoded with a small protobuf wire parser so
no generated code is needed.
"""

from __future__ import annotations

import bz2
import hashlib
import logging
import lzma
import struct
import zipfile
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO

from sudroid.errors import PreconditionError

log = logging.getLogger(__name__)

MAGIC = b"CrAU"
MAX_OP_DATA = 1 << 30  # 1 GiB per operation blob
OP_REPLACE = 0
OP_REPLACE_BZ = 1
OP_ZERO = 6
OP_REPLACE_XZ = 8
SUPPORTED_OPS = {OP_REPLACE, OP_REPLACE_BZ, OP_ZERO, OP_REPLACE_XZ}
OP_NAMES = {
    0: "REPLACE",
    1: "REPLACE_BZ",
    2: "MOVE",
    3: "BSDIFF",
    4: "SOURCE_COPY",
    5: "SOURCE_BSDIFF",
    6: "ZERO",
    7: "DISCARD",
    8: "REPLACE_XZ",
    9: "PUFFDIFF",
    10: "BROTLI_BSDIFF",
    11: "ZUCCHINI",
    12: "LZ4DIFF_BSDIFF",
    13: "LZ4DIFF_PUFFDIFF",
}


class PayloadError(PreconditionError):
    pass


# --- protobuf wire format -------------------------------------------------


def _varint(buf: bytes, pos: int) -> tuple[int, int]:
    result = 0
    shift = 0
    while True:
        if pos >= len(buf):
            raise PayloadError("truncated protobuf varint")
        b = buf[pos]
        pos += 1
        result |= (b & 0x7F) << shift
        if not b & 0x80:
            return result, pos
        shift += 7
        if shift > 70:
            raise PayloadError("protobuf varint too long")


def iter_fields(buf: bytes) -> Iterator[tuple[int, int, int | bytes]]:
    """Yield (field_number, wire_type, value). Length delimited values are bytes."""
    pos = 0
    while pos < len(buf):
        tag, pos = _varint(buf, pos)
        field_no, wire = tag >> 3, tag & 7
        if wire == 0:
            val, pos = _varint(buf, pos)
            yield field_no, wire, val
        elif wire == 1:
            if pos + 8 > len(buf):
                raise PayloadError("truncated fixed64")
            yield field_no, wire, struct.unpack_from("<Q", buf, pos)[0]
            pos += 8
        elif wire == 2:
            length, pos = _varint(buf, pos)
            if pos + length > len(buf):
                raise PayloadError("truncated length delimited field")
            yield field_no, wire, bytes(buf[pos : pos + length])
            pos += length
        elif wire == 5:
            if pos + 4 > len(buf):
                raise PayloadError("truncated fixed32")
            yield field_no, wire, struct.unpack_from("<I", buf, pos)[0]
            pos += 4
        else:
            raise PayloadError(f"unsupported protobuf wire type {wire}")


# --- manifest model ---------------------------------------------------------


@dataclass(frozen=True)
class Extent:
    start_block: int
    num_blocks: int


@dataclass(frozen=True)
class Operation:
    type: int
    data_offset: int
    data_length: int
    dst_extents: tuple[Extent, ...]
    sha256: bytes = b""


@dataclass
class Partition:
    name: str
    ops: list[Operation] = field(default_factory=list)
    size: int = 0
    hash: bytes = b""


@dataclass
class Payload:
    block_size: int
    partitions: dict[str, Partition]
    data_offset: int
    source: BinaryIO

    def names(self) -> list[str]:
        return list(self.partitions)


def _parse_extent(buf: bytes) -> Extent:
    start = num = 0
    for fno, _, val in iter_fields(buf):
        if fno == 1 and isinstance(val, int):
            start = val
        elif fno == 2 and isinstance(val, int):
            num = val
    return Extent(start, num)


def _parse_operation(buf: bytes) -> Operation:
    typ = off = length = 0
    extents: list[Extent] = []
    sha = b""
    for fno, _, val in iter_fields(buf):
        if fno == 1 and isinstance(val, int):
            typ = val
        elif fno == 2 and isinstance(val, int):
            off = val
        elif fno == 3 and isinstance(val, int):
            length = val
        elif fno == 6 and isinstance(val, bytes):
            extents.append(_parse_extent(val))
        elif fno == 8 and isinstance(val, bytes):
            sha = val
    return Operation(typ, off, length, tuple(extents), sha)


def _parse_partition(buf: bytes) -> Partition:
    part = Partition(name="")
    for fno, _, val in iter_fields(buf):
        if fno == 1 and isinstance(val, bytes):
            part.name = val.decode("utf-8", errors="replace")
        elif fno == 8 and isinstance(val, bytes):
            part.ops.append(_parse_operation(val))
        elif fno == 7 and isinstance(val, bytes):
            for ifno, _, ival in iter_fields(val):
                if ifno == 1 and isinstance(ival, int):
                    part.size = ival
                elif ifno == 2 and isinstance(ival, bytes):
                    part.hash = ival
    return part


def open_payload(fh: BinaryIO) -> Payload:
    head = fh.read(24)
    if len(head) < 24 or head[:4] != MAGIC:
        raise PayloadError("not a payload.bin (bad magic)")
    version = struct.unpack_from(">Q", head, 4)[0]
    manifest_size = struct.unpack_from(">Q", head, 12)[0]
    if version != 2:
        raise PayloadError(f"unsupported payload version {version}")
    metadata_sig_size = struct.unpack_from(">I", head, 20)[0]
    if manifest_size > 256 * 1024 * 1024:
        raise PayloadError("manifest too large")
    manifest = fh.read(manifest_size)
    if len(manifest) != manifest_size:
        raise PayloadError("truncated manifest")
    data_offset = 24 + manifest_size + metadata_sig_size
    block_size = 4096
    partitions: dict[str, Partition] = {}
    for fno, _, val in iter_fields(manifest):
        if fno == 3 and isinstance(val, int):
            block_size = val
        elif fno == 13 and isinstance(val, bytes):
            part = _parse_partition(val)
            if part.name:
                partitions[part.name] = part
    if not partitions:
        raise PayloadError("payload has no partitions")
    return Payload(block_size, partitions, data_offset, fh)


def extract(payload: Payload, name: str, out: Path) -> Path:
    part = payload.partitions.get(name)
    if part is None:
        raise PayloadError(
            f"partition {name} not in payload", hint=f"available: {', '.join(payload.names())}"
        )
    unsupported = [op for op in part.ops if op.type not in SUPPORTED_OPS]
    if unsupported:
        kinds = sorted({OP_NAMES.get(op.type, str(op.type)) for op in unsupported})
        raise PayloadError(
            f"{name} uses {', '.join(kinds)} operations; this is an incremental OTA",
            hint="Use a full OTA package or the factory image.",
        )
    out.parent.mkdir(parents=True, exist_ok=True)
    bs = payload.block_size
    total = part.size or max(
        ((e.start_block + e.num_blocks) * bs for op in part.ops for e in op.dst_extents),
        default=0,
    )
    with out.open("wb") as dst:
        dst.truncate(total)
        for op in part.ops:
            if op.type == OP_ZERO:
                continue
            if op.data_length > MAX_OP_DATA:
                raise PayloadError(f"operation in {name} claims {op.data_length} bytes; refusing")
            payload.source.seek(payload.data_offset + op.data_offset)
            blob = payload.source.read(op.data_length)
            if len(blob) != op.data_length:
                raise PayloadError(f"truncated data for {name}")
            if op.sha256 and hashlib.sha256(blob).digest() != op.sha256:
                raise PayloadError(f"data hash mismatch in {name}")
            if op.type == OP_REPLACE_BZ:
                blob = bz2.decompress(blob)
            elif op.type == OP_REPLACE_XZ:
                blob = lzma.decompress(blob)
            pos = 0
            for ext in op.dst_extents:
                length = ext.num_blocks * bs
                dst.seek(ext.start_block * bs)
                dst.write(blob[pos : pos + length])
                pos += length
    if part.hash:
        digest = hashlib.sha256()
        with out.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                digest.update(chunk)
        if digest.digest() != part.hash:
            raise PayloadError(f"{name} hash mismatch after extraction")
    log.info("extracted %s (%d bytes) from payload", name, total)
    return out


def extract_from_file(path: Path, names: Iterable[str], dest: Path) -> dict[str, Path]:
    with path.open("rb") as fh:
        payload = open_payload(fh)
        return _extract_many(payload, names, dest)


def extract_from_zip(zip_path: Path, names: Iterable[str], dest: Path) -> dict[str, Path]:
    with zipfile.ZipFile(zip_path) as zf:
        try:
            info = zf.getinfo("payload.bin")
        except KeyError:
            raise PayloadError(f"{zip_path.name} has no payload.bin") from None
        if info.compress_type != zipfile.ZIP_STORED:
            # Seeking inside a deflated entry re-inflates from the start on every seek.
            # Extract once to a temp file next to the destination instead.
            log.info("payload.bin is compressed in the zip, extracting first")
            dest.mkdir(parents=True, exist_ok=True)
            tmp = dest / "payload.bin"
            with zf.open(info) as src, tmp.open("wb") as out:
                for chunk in iter(lambda: src.read(1 << 20), b""):
                    out.write(chunk)
            try:
                return extract_from_file(tmp, names, dest)
            finally:
                tmp.unlink(missing_ok=True)
        with zf.open(info) as fh:
            payload = open_payload(fh)  # type: ignore[arg-type]
            return _extract_many(payload, names, dest)


def _extract_many(payload: Payload, names: Iterable[str], dest: Path) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for n in names:
        part = n[:-4] if n.endswith(".img") else n
        if part in payload.partitions:
            out[f"{part}.img"] = extract(payload, part, dest / f"{part}.img")
    if not out:
        raise PayloadError(
            "none of the requested partitions are in the payload",
            hint=f"available: {', '.join(payload.names())}",
        )
    return out
