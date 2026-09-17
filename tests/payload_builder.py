"""Tiny protobuf encoder to build synthetic payload.bin files for tests."""

from __future__ import annotations

import bz2
import hashlib
import io
import lzma
import struct
import zipfile
from pathlib import Path


def varint(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def field_varint(fno: int, val: int) -> bytes:
    return varint((fno << 3) | 0) + varint(val)


def field_bytes(fno: int, val: bytes) -> bytes:
    return varint((fno << 3) | 2) + varint(len(val)) + val


def extent(start: int, num: int) -> bytes:
    return field_varint(1, start) + field_varint(2, num)


class PayloadBuilder:
    def __init__(self, block_size: int = 4096) -> None:
        self.block_size = block_size
        self.data = bytearray()
        self.partitions: list[bytes] = []

    def add(
        self,
        name: str,
        image: bytes,
        *,
        mode: str = "replace",
        ops_split: int = 1,
        op_type_override: int | None = None,
    ) -> None:
        bs = self.block_size
        padded = image + b"\x00" * (-len(image) % bs)
        nblocks = len(padded) // bs
        per = max(1, nblocks // ops_split)
        ops = b""
        start = 0
        while start < nblocks:
            count = min(per, nblocks - start)
            chunk = padded[start * bs : (start + count) * bs]
            if mode == "zero" or (mode == "auto" and not any(chunk)):
                typ, blob = 6, b""
            elif mode == "bz":
                typ, blob = 1, bz2.compress(chunk)
            elif mode == "xz":
                typ, blob = 8, lzma.compress(chunk)
            else:
                typ, blob = 0, chunk
            if op_type_override is not None:
                typ = op_type_override
            op = field_varint(1, typ)
            if blob:
                op += field_varint(2, len(self.data)) + field_varint(3, len(blob))
                op += field_bytes(8, hashlib.sha256(blob).digest())
                self.data += blob
            op += field_bytes(6, extent(start, count))
            ops += field_bytes(8, op)
            start += count
        info = field_varint(1, len(padded)) + field_bytes(2, hashlib.sha256(padded).digest())
        part = field_bytes(1, name.encode()) + ops + field_bytes(7, info)
        self.partitions.append(part)

    def build(self, sig_size: int = 8) -> bytes:
        manifest = field_varint(3, self.block_size) + b"".join(
            field_bytes(13, p) for p in self.partitions
        )
        head = (
            b"CrAU"
            + struct.pack(">Q", 2)
            + struct.pack(">Q", len(manifest))
            + struct.pack(">I", sig_size)
        )
        return head + manifest + b"\xaa" * sig_size + bytes(self.data)

    def write_zip(self, path: Path) -> Path:
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr(
                zipfile.ZipInfo("payload.bin"), self.build(), compress_type=zipfile.ZIP_STORED
            )
            zf.writestr("payload_properties.txt", "FILE_HASH=x\n")
        return path


def padded(image: bytes, bs: int = 4096) -> bytes:
    return image + b"\x00" * (-len(image) % bs)


def as_io(data: bytes) -> io.BytesIO:
    return io.BytesIO(data)
