"""Run Magisk's own boot_patch.sh on the device over adb.

The device ABI binaries and scripts come from the same APK that will be
installed, so the patch logic always matches the Magisk version.
"""

from __future__ import annotations

import logging
import shlex
from dataclasses import dataclass
from pathlib import Path

from sudroid.errors import PatchError
from sudroid.images.verify import inspect
from sudroid.root.apk import MagiskBundle
from sudroid.tools.adb import AdbClient

log = logging.getLogger(__name__)

REMOTE_DIR = "/data/local/tmp/sudroid"


@dataclass
class PatchOptions:
    keep_verity: bool = True
    keep_force_encrypt: bool = True
    patch_vbmeta: bool = False
    recovery_mode: bool = False
    legacy_sar: bool = False

    def env(self) -> str:
        def b(v: bool) -> str:
            return "true" if v else "false"

        return (
            f"KEEPVERITY={b(self.keep_verity)} "
            f"KEEPFORCEENCRYPT={b(self.keep_force_encrypt)} "
            f"PATCHVBMETAFLAG={b(self.patch_vbmeta)} "
            f"RECOVERYMODE={b(self.recovery_mode)} "
            f"LEGACYSAR={b(self.legacy_sar)}"
        )


@dataclass(frozen=True)
class PatchResult:
    image: Path
    magisk_version: str
    log: str


class DevicePatcher:
    def __init__(self, adb: AdbClient, bundle: MagiskBundle) -> None:
        self._adb = adb
        self._bundle = bundle

    def patch(self, stock: Path, out: Path, opts: PatchOptions | None = None) -> PatchResult:
        opts = opts or PatchOptions()
        adb = self._adb
        info = inspect(stock)
        if not info.is_boot:
            raise PatchError(
                f"{stock.name} is not a boot image (kind={info.kind})",
                hint="Give the stock boot.img or init_boot.img for this exact build.",
            )
        log.info(
            "patching %s (header v%d, %d bytes) on device",
            stock.name,
            info.header_version,
            info.size,
        )

        self._shell_ok(f"rm -rf {REMOTE_DIR} && mkdir -p {REMOTE_DIR}", mutating=True)
        try:
            for name in self._bundle.files:
                if name == "magisk.apk":
                    continue
                r = adb.push(self._bundle.dir / name, f"{REMOTE_DIR}/{name}")
                if not r.ok:
                    raise PatchError(f"push {name} failed: {r.err}")
            r = adb.push(stock, f"{REMOTE_DIR}/stock.img")
            if not r.ok:
                raise PatchError(f"push stock image failed: {r.err}")
            self._shell_ok(f"chmod -R 755 {REMOTE_DIR}", mutating=True)

            cmd = f"cd {REMOTE_DIR} && {opts.env()} sh ./boot_patch.sh ./stock.img"
            r = adb._runner.run([*adb._base(), "shell", cmd], timeout=600, mutating=True)
            output = r.combined
            log.debug("boot_patch.sh output:\n%s", output)
            if not r.ok or "new-boot.img" not in self._shell(f"ls {REMOTE_DIR}").text:
                raise PatchError(
                    "boot_patch.sh failed on device",
                    hint=_tail(output),
                )
            if "! " in output and "Unsupported" in output:
                raise PatchError("Magisk reports unsupported image", hint=_tail(output))

            out.parent.mkdir(parents=True, exist_ok=True)
            r = adb.pull(f"{REMOTE_DIR}/new-boot.img", out)
            if not r.ok or not out.is_file():
                raise PatchError(f"pull patched image failed: {r.err}")
            patched = inspect(out)
            if not patched.is_boot or not patched.has_ramdisk:
                raise PatchError(
                    "patched image failed sanity check",
                    hint=f"kind={patched.kind} ramdisk={patched.ramdisk_size}",
                )
            version = _version_from_output(output) or self._bundle.version
            log.info("patched image written to %s (%d bytes)", out, patched.size)
            return PatchResult(out, version, output)
        finally:
            self._shell(f"rm -rf {REMOTE_DIR}", mutating=True)

    def _shell(self, cmd: str, *, mutating: bool = False):  # type: ignore[no-untyped-def]
        return self._adb._runner.run(
            [*self._adb._base(), "shell", cmd], timeout=120, mutating=mutating
        )

    def _shell_ok(self, cmd: str, *, mutating: bool = False) -> None:
        r = self._shell(cmd, mutating=mutating)
        if not r.ok:
            raise PatchError(f"device command failed: {shlex.split(cmd)[0]}", hint=r.err)


def _tail(text: str, n: int = 15) -> str:
    lines = [ln for ln in text.splitlines() if ln.strip()]
    return "\n".join(lines[-n:])


def _version_from_output(text: str) -> str:
    """boot_patch.sh prints '- Installing: 28.0 (28000)'."""
    for line in text.splitlines():
        if "Installing:" in line:
            rest = line.split("Installing:", 1)[1].strip()
            return rest.split()[0] if rest else ""
    return ""
