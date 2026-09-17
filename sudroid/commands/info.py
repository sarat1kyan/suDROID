from __future__ import annotations

import dataclasses
import json

from sudroid.context import AppContext, detect_device
from sudroid.device.profiles import profile_for
from sudroid.ui.render import device_table, lock_hint, quirks_table


def run(ctx: AppContext) -> None:
    device = detect_device(ctx)
    profile = profile_for(device)
    quirks = profile.quirks(device)
    if ctx.json:
        data = dataclasses.asdict(device)
        data["profile"] = profile.name
        data["flash_backend"] = profile.flash_backend.value
        data["effective_patch_target"] = profile.patch_target(device).value
        data["quirks"] = [dataclasses.asdict(q) for q in quirks]
        print(json.dumps(data, indent=2, default=str))
        return
    ctx.console.print(device_table(device, profile))
    if quirks:
        ctx.console.print()
        ctx.console.print(quirks_table(quirks))
    hint = lock_hint(device)
    if hint:
        ctx.console.print()
        ctx.console.print(f"[yellow]{hint}[/]")
