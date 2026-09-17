from __future__ import annotations

from pathlib import Path

from sudroid.backup.manager import BackupManager
from sudroid.context import AppContext, detect_device
from sudroid.device.model import FlashBackend
from sudroid.device.profiles import profile_for
from sudroid.errors import PreconditionError
from sudroid.paths import data_dir
from sudroid.ui import prompts
from sudroid.workflow import session as sm
from sudroid.workflow.engine import Engine, Runtime
from sudroid.workflow.steps import FlashImage, WaitBoot


def run(ctx: AppContext, *, partition: str | None = None, backup_id: str | None = None) -> None:
    device = detect_device(ctx)
    profile = profile_for(device)
    if profile.flash_backend is not FlashBackend.FASTBOOT:
        raise PreconditionError(f"{profile.name} restore needs {profile.flash_backend.value}")
    bm = BackupManager(ctx.config.backup_dir)
    target = partition or profile.patch_target(device).value
    if backup_id:
        entry = next((e for e in bm.list(device.serial) if e.id == backup_id), None)
    else:
        entry = bm.latest(device.serial, target, device.build_id) or bm.latest(
            device.serial, target
        )
    if entry is None:
        raise PreconditionError(
            f"no backup of {target} for {device.serial}", hint="See `sudroid backup --list`."
        )
    chosen = entry
    if not bm.verify(chosen):
        raise PreconditionError(f"backup {chosen.id} failed checksum")
    if chosen.build_id != device.build_id:
        ctx.console.print(
            f"[yellow]backup build {chosen.build_id} differs from installed {device.build_id}[/]"
        )
    session = sm.new_session(device.serial, "restore")
    rt = Runtime(ctx, device, profile, session, data_dir() / "work" / session.id)
    rt.data["patched"] = chosen.path
    rt.data["stock"] = chosen.path

    class RestoreFlash(FlashImage):
        title = "Flash stock image"

        def describe(self, rt: Runtime) -> str:
            return f"Restore {chosen.id} to {target}"

        def undo(self, rt: Runtime) -> None:
            return None

    if not ctx.dry_run:
        prompts.require(ctx, f"Restore {chosen.id} ({chosen.size} bytes) to {target}?")
    Engine(rt, [RestoreFlash(), WaitBoot()]).run()
    ctx.console.print(f"[green]restored[/] {target} from {Path(chosen.path).name}")
