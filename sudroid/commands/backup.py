from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from rich.table import Table

from sudroid.backup.manager import BackupManager
from sudroid.context import AppContext, detect_device
from sudroid.device.profiles import profile_for
from sudroid.errors import PreconditionError
from sudroid.images.verify import inspect
from sudroid.paths import data_dir
from sudroid.workflow import session as sm
from sudroid.workflow.engine import Runtime
from sudroid.workflow.steps import AcquireImage, partition_of


def run(
    ctx: AppContext,
    *,
    image: Path | None = None,
    partition: str | None = None,
    list_only: bool = False,
) -> None:
    device = detect_device(ctx)
    profile = profile_for(device)
    bm = BackupManager(ctx.config.backup_dir)
    if list_only:
        entries = bm.list(device.serial)
        if ctx.json:
            print(json.dumps([dataclasses.asdict(e) for e in entries], indent=2))
            return
        t = Table(title=f"Backups for {device.serial}")
        for col in ("id", "partition", "slot", "build", "size", "source", "ok"):
            t.add_column(col)
        for e in entries:
            t.add_row(
                e.id,
                e.partition,
                e.slot,
                e.build_id,
                str(e.size),
                e.source,
                "yes" if bm.verify(e) else "MISSING",
            )
        ctx.console.print(t)
        return

    target = partition or profile.patch_target(device).value
    if target not in {"boot", "init_boot", "vendor_boot"}:
        raise PreconditionError(f"unsupported partition {target}")
    session = sm.new_session(device.serial, "backup")
    rt = Runtime(ctx, device, profile, session, data_dir() / "work" / session.id)
    if image:
        info = inspect(image)
        if not info.is_boot and target != "vendor_boot":
            raise PreconditionError(f"{image.name} is not a boot image (kind={info.kind})")
        rt.data["image"] = str(image)
    elif not device.root_present:
        raise PreconditionError(
            "no image given and device is not rooted",
            hint="Pass --image <stock image> or root first.",
        )
    AcquireImage().run(rt)
    entry = bm.save(device, target, Path(rt.data["stock"]), rt.data.get("stock_source", "unknown"))
    ctx.console.print(f"[green]saved[/] {entry.path} ({partition_of(rt)} on {device.model})")
