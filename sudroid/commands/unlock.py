from __future__ import annotations

import logging

from rich.prompt import Prompt

from sudroid.backup.manager import BackupManager
from sudroid.context import AppContext, detect_device
from sudroid.device.model import Vendor
from sudroid.device.profiles import profile_for
from sudroid.errors import FlashError, PreconditionError
from sudroid.tools.base import Result
from sudroid.tools.fastboot import FastbootClient
from sudroid.ui import prompts
from sudroid.ui.render import quirks_table

log = logging.getLogger(__name__)


def _fastboot(fb: FastbootClient, cmd: list[str], *, read: bool = False) -> Result:
    """Dispatch a profile command like ["oem", "unlock", KEY] or ["flashing", "unlock"]."""
    head, rest = cmd[0], cmd[1:]
    if head == "flashing":
        return fb.flashing(*rest)
    if head == "oem":
        return fb.oem_read(*rest) if read else fb.oem(*rest)
    raise PreconditionError(f"unsupported fastboot command from profile: {' '.join(cmd)}")


def _print_guide(ctx: AppContext, steps: list[str], url: str) -> None:
    for i, step in enumerate(steps, 1):
        ctx.console.print(f"  {i}. {step}")
    if url:
        ctx.console.print(f"  reference: {url}")


def run(ctx: AppContext, *, i_know: bool = False) -> None:
    device = detect_device(ctx)
    profile = profile_for(device)
    quirks = profile.quirks(device)
    if quirks:
        ctx.console.print(quirks_table(quirks))
    if any(q.severity == "block" for q in quirks):
        raise PreconditionError(
            "unlock blocked for this device", hint="; ".join(q.message for q in quirks)
        )

    if device.is_unlocked:
        ctx.console.print("[green]bootloader is already unlocked[/]")
        return

    ctx.console.print(f"[bold]Unlock steps for {profile.name}[/]")
    _print_guide(ctx, profile.unlock_steps(device), profile.unlock_url)

    if device.oem_unlock_allowed is False:
        raise PreconditionError(
            "OEM unlocking is disabled",
            hint="Settings > Developer options > OEM unlocking. Then run this again.",
        )

    if not profile.unlock_automatable or not (
        profile.unlock_commands(device) or profile.needs_unlock_data(device)
    ):
        ctx.console.print(
            "[yellow]this vendor cannot be unlocked from the host; follow the steps above[/]"
        )
        return

    if not i_know and not BackupManager(ctx.config.backup_dir).has_backup(device.serial):
        raise PreconditionError(
            "no stock image backup for this device",
            hint="Run `sudroid backup --image <stock boot or init_boot>` first, or pass --i-know.",
        )

    if profile.unlock_wipes_data:
        prompts.typed_confirm(
            ctx,
            "UNLOCK",
            f"Unlocking wipes ALL data on {device.model} ({device.serial}) and may void warranty.",
        )

    adb = ctx.adb()
    fb = ctx.fastboot()
    if not fb.devices():
        ctx.console.print("rebooting to bootloader...")
        adb.reboot("bootloader")
        if not fb.wait(timeout=120) and not ctx.dry_run:
            raise FlashError(
                "device did not enter fastboot", hint="Enter the bootloader manually and retry."
            )

    if profile.needs_unlock_data(device):
        data_cmd = profile.unlock_data_command(device)
        if data_cmd:
            r = _fastboot(fb, data_cmd, read=True)
            lines = [
                ln.replace("(bootloader)", "").strip()
                for ln in r.combined.splitlines()
                if "(bootloader)" in ln or ln.strip()
            ]
            joined = "".join(ln for ln in lines if ln and not ln.startswith(("OKAY", "Finished")))
            ctx.console.print("[bold]unlock data:[/]")
            ctx.console.print(joined)
            if device.vendor is Vendor.MOTOROLA:
                ctx.console.print("paste it on the Motorola unlock page, then enter the key below")
        else:
            ctx.console.print("request the unlock code from the vendor site using your IMEI")
        key = Prompt.ask("unlock key", console=ctx.console).strip()
        if not key:
            raise PreconditionError("no unlock key entered")
        cmd = profile.unlock_command_with_key(device, key)
        if cmd is None:
            raise PreconditionError("profile has no keyed unlock command")
        r = _fastboot(fb, cmd)
        if not r.ok and not ctx.dry_run:
            raise FlashError("unlock command failed", hint=r.combined)
    else:
        ok = False
        for cmd in profile.unlock_commands(device):
            ctx.console.print(f"fastboot {' '.join(cmd)}  (confirm on the phone)")
            r = _fastboot(fb, cmd)
            if r.ok or ctx.dry_run:
                ok = True
                break
            log.warning("fastboot %s failed: %s", " ".join(cmd), r.combined)
        if not ok:
            raise FlashError(
                "all unlock commands failed",
                hint="Check OEM unlocking is on and the phone screen for a confirmation prompt.",
            )

    state = fb.unlocked()
    if state is False and not ctx.dry_run:
        raise FlashError("device still reports locked", hint="Confirm on the phone and rerun.")
    fb.reboot()
    ctx.console.print(
        "[green]unlock issued.[/] The device wipes and reboots. Finish setup, re-enable USB "
        "debugging and OEM unlocking, then run `sudroid root`."
    )
