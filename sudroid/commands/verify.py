from __future__ import annotations

import json

from rich.table import Table

from sudroid.context import AppContext, detect_device


def run(ctx: AppContext) -> None:
    device = detect_device(ctx)
    adb = ctx.adb()
    rows: list[tuple[str, str]] = []
    su = adb.root_shell("id")
    rows.append(("su -c id", su.text if su.ok else (su.err or "denied")))
    rooted = "uid=0" in su.text
    if rooted:
        for name, cmd in (("magisk", "magisk -v"), ("kernelsu", "ksud -V"), ("apatch", "apd -V")):
            r = adb.root_shell(cmd)
            rows.append((name, r.text if r.ok and r.text else "not found"))
    rows.append(("detected", device.root_present or "none"))
    if ctx.json:
        print(json.dumps({"rooted": rooted, "checks": dict(rows)}, indent=2))
        return
    t = Table(title=f"Root status: {device.model}")
    t.add_column("check")
    t.add_column("result")
    for k, v in rows:
        t.add_row(k, v)
    ctx.console.print(t)
    ctx.console.print("[green]rooted[/]" if rooted else "[yellow]not rooted[/]")
