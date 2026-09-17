"""Samsung specific steps: download mode, Heimdall flash, Odin tar fallback."""

from __future__ import annotations

import logging
from pathlib import Path

from sudroid.errors import FlashError, PreconditionError, ToolMissingError
from sudroid.images.samsung import build_odin_tar
from sudroid.images.verify import patch_vbmeta_flags
from sudroid.tools.heimdall import HeimdallClient
from sudroid.workflow.engine import Runtime, Step
from sudroid.workflow.steps import partition_of, target_of

log = logging.getLogger(__name__)

VBMETA_PARTITION = "VBMETA"


def heimdall_of(rt: Runtime) -> HeimdallClient:
    return HeimdallClient(rt.ctx.runner, str(rt.ctx.tool_path("heimdall")))


def odin_mode(rt: Runtime) -> bool:
    return bool(rt.data.get("odin"))


class CheckHeimdall(Step):
    name = "check_heimdall"
    title = "Check Heimdall"

    def skip(self, rt: Runtime) -> str:
        return "Odin tar requested" if odin_mode(rt) else ""

    def run(self, rt: Runtime) -> None:
        try:
            path = rt.ctx.tool_path("heimdall")
        except ToolMissingError as exc:
            raise PreconditionError(
                "Heimdall not found",
                hint=(exc.hint or "") + " Or pass --odin to get a tar for Odin on Windows.",
            ) from None
        rt.say(f"heimdall: {path}")


class PatchVbmeta(Step):
    name = "patch_vbmeta"
    title = "Patch vbmeta flags"

    def skip(self, rt: Runtime) -> str:
        return "" if rt.data.get("vbmeta") else "no vbmeta image in firmware"

    def run(self, rt: Runtime) -> None:
        src = Path(rt.data["vbmeta"])
        out = rt.work / "patched_vbmeta.img"
        try:
            out.write_bytes(patch_vbmeta_flags(src.read_bytes()))
        except ValueError as exc:
            raise PreconditionError(f"vbmeta patch failed: {exc}") from None
        rt.data["patched_vbmeta"] = str(out)
        rt.say("vbmeta: verification and hashtree disabled flags set")


def _images(rt: Runtime, *, stock: bool = False) -> dict[str, Path]:
    key_img = "backup_path" if stock else "patched"
    key_vb = "vbmeta" if stock else "patched_vbmeta"
    img = rt.data.get(key_img) or rt.data.get("stock" if stock else "patched")
    if not img:
        raise PreconditionError("no image to flash in session")
    out = {partition_of(rt): Path(img)}
    vb = rt.data.get(key_vb)
    if vb:
        out[VBMETA_PARTITION] = Path(vb)
    return out


class OdinTarOut(Step):
    name = "odin_tar"
    title = "Write Odin tar"

    def skip(self, rt: Runtime) -> str:
        return "" if odin_mode(rt) else "Heimdall flashes directly"

    def run(self, rt: Runtime) -> None:
        images = _images(rt)
        entries = {f"{target_of(rt).value}.img": images[partition_of(rt)]}
        if VBMETA_PARTITION in images:
            entries["vbmeta.img"] = images[VBMETA_PARTITION]
        tar = build_odin_tar(entries, rt.work / "magisk_patched.tar")
        rt.data["odin_tar"] = str(tar)
        rt.say(f"[green]Odin tar:[/] {tar}")
        for i, line in enumerate(
            [
                "Power off. Hold Volume Up + Volume Down, plug in USB, press Volume Up "
                "(download mode).",
                "Open Odin on Windows, wait for the COM port to show blue.",
                f"Click AP, select {tar.name}.",
                "Options: keep Auto Reboot on, F. Reset Time on. Leave Re-Partition off.",
                "Click Start. Wait for PASS. The device reboots.",
                "Re-enable USB debugging, then run: sudroid verify",
            ],
            1,
        ):
            rt.say(f"  {i}. {line}")


class EnterDownloadMode(Step):
    name = "enter_download"
    title = "Enter download mode"
    mutating = True

    def skip(self, rt: Runtime) -> str:
        if odin_mode(rt):
            return "Odin tar requested"
        return "dry-run" if rt.ctx.dry_run else ""

    def run(self, rt: Runtime) -> None:
        h = heimdall_of(rt)
        if h.detect():
            return
        adb = rt.ctx.adb()
        if any(d.ready for d in adb.devices()):
            adb.reboot("download")
        rt.say("waiting for download mode...")
        if not h.wait(timeout=180):
            raise FlashError(
                "device not detected in download mode",
                hint="Hold Volume Up + Volume Down and plug in USB, press Volume Up, then rerun "
                "with --resume.",
            )


class HeimdallFlash(Step):
    name = "heimdall_flash"
    title = "Flash with Heimdall"
    mutating = True

    def skip(self, rt: Runtime) -> str:
        return "Odin tar requested" if odin_mode(rt) else ""

    def describe(self, rt: Runtime) -> str:
        return f"Flash patched image to {partition_of(rt)} with Heimdall"

    def check(self, rt: Runtime) -> None:
        if not rt.data.get("patched"):
            raise PreconditionError("no patched image in session")

    def run(self, rt: Runtime) -> None:
        h = heimdall_of(rt)
        images = _images(rt)
        pit = h.print_pit()
        if pit:
            missing = [p for p in images if p not in pit]
            if missing:
                raise FlashError(
                    f"partitions not in PIT: {', '.join(missing)}",
                    hint=f"PIT has: {', '.join(pit)}",
                )
        r = h.flash(images)
        if not r.ok and not rt.ctx.dry_run:
            raise FlashError("heimdall flash failed", hint=r.combined[-800:])
        rt.data["flashed_partition"] = partition_of(rt)
        rt.say(f"flashed {', '.join(images)}")

    def undo(self, rt: Runtime) -> None:
        if not rt.data.get("flashed_partition"):
            return
        h = heimdall_of(rt)
        images = _images(rt, stock=True)
        rt.say(f"restoring {', '.join(images)} with Heimdall")
        if not h.detect() and not h.wait(timeout=180):
            raise FlashError("device not in download mode for restore")
        r = h.flash(images)
        if not r.ok:
            raise FlashError("heimdall restore failed", hint=r.combined[-800:])
