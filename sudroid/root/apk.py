"""Extract the patch toolkit from a Magisk APK for a device ABI."""

from __future__ import annotations

import logging
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path

from sudroid.errors import PatchError

log = logging.getLogger(__name__)

_LIB = re.compile(r"^lib/(?P<abi>[^/]+)/lib(?P<name>[^/]+)\.so$")
ABI_32_FOR = {"arm64-v8a": "armeabi-v7a", "x86_64": "x86"}


@dataclass(frozen=True)
class MagiskBundle:
    dir: Path
    version: str
    abi: str
    files: tuple[str, ...]

    @property
    def apk(self) -> Path:
        return self.dir / "magisk.apk"


def extract_bundle(apk: Path, abi: str, dest: Path, version: str = "") -> MagiskBundle:
    dest.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    with zipfile.ZipFile(apk) as zf:
        names = zf.namelist()
        abis = {m.group("abi") for n in names if (m := _LIB.match(n))}
        if abi not in abis:
            raise PatchError(
                f"Magisk APK has no native libs for {abi}", hint=f"available: {sorted(abis)}"
            )
        for n in names:
            if n.startswith("assets/") and (n.endswith(".sh") or n.endswith(".apk")):
                out = dest / Path(n).name
                out.write_bytes(zf.read(n))
                written.append(out.name)
            m = _LIB.match(n)
            if m and m.group("abi") == abi:
                out = dest / m.group("name")
                out.write_bytes(zf.read(n))
                written.append(out.name)
        # 64-bit devices also need the 32-bit magisk binary for zygisk on older Magisk.
        abi32 = ABI_32_FOR.get(abi)
        if abi32 and "magisk32" not in written:
            for n in names:
                m = _LIB.match(n)
                if m and m.group("abi") == abi32 and m.group("name") in {"magisk32", "magisk"}:
                    out = dest / "magisk32"
                    out.write_bytes(zf.read(n))
                    written.append(out.name)
                    break
    (dest / "magisk.apk").write_bytes(apk.read_bytes())
    written.append("magisk.apk")
    if "boot_patch.sh" not in written or "magiskboot" not in written or "magiskinit" not in written:
        raise PatchError("Magisk APK is missing boot_patch.sh, magiskboot or magiskinit")
    log.debug("extracted %s for %s: %s", apk.name, abi, written)
    return MagiskBundle(dest, version, abi, tuple(sorted(set(written))))
