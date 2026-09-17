from __future__ import annotations

from pathlib import Path

from sudroid.context import AppContext, detect_device
from sudroid.device.profiles import profile_for
from sudroid.errors import PreconditionError
from sudroid.paths import data_dir
from sudroid.workflow import session as sm
from sudroid.workflow.engine import Engine, Runtime
from sudroid.workflow.steps import AcquireImage, CheckTools, FetchMagisk, PatchImage


def run(ctx: AppContext, image: Path, *, out: Path | None = None, magisk_version: str = "") -> None:
    if not image.is_file():
        raise PreconditionError(f"image not found: {image}")
    device = detect_device(ctx)
    profile = profile_for(device)
    session = sm.new_session(device.serial, "patch")
    rt = Runtime(ctx, device, profile, session, data_dir() / "work" / session.id)
    rt.data["image"] = str(image)
    rt.data["skip_backup"] = "1"
    if magisk_version:
        rt.data["magisk_version"] = magisk_version
    Engine(rt, [CheckTools(), AcquireImage(), FetchMagisk(), PatchImage()]).run()
    patched = Path(rt.data.get("patched", ""))
    if out and patched.is_file():
        out.parent.mkdir(parents=True, exist_ok=True)
        patched.replace(out)
        patched = out
    if patched.is_file():
        ctx.console.print(f"[green]patched image:[/] {patched}")
