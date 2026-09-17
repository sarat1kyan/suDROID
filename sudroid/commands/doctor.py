from __future__ import annotations

import glob
import json
import platform
import sys

from sudroid.context import AppContext
from sudroid.errors import ToolMissingError
from sudroid.tools import platform_tools
from sudroid.ui.render import doctor_table

Row = tuple[str, str, str]


def _tool_row(ctx: AppContext, name: str, required: bool) -> tuple[Row, bool]:
    try:
        path = ctx.tool_path(name)
    except ToolMissingError as exc:
        status = "fail" if required else "warn"
        return (name, status, exc.hint or exc.message), not required
    ver = platform_tools.version(path, name) if not _is_fake(ctx) else "ok"
    return (name, "ok", f"{path} ({ver})"), True


def _is_fake(ctx: AppContext) -> bool:
    return type(ctx.runner).__name__ in {"FakeRunner", "DryRunRunner"}


def collect(ctx: AppContext) -> tuple[list[Row], bool]:
    rows: list[Row] = []
    ok = True
    rows.append(("python", "ok", sys.version.split()[0]))
    rows.append(("host", "ok", f"{platform_tools.host_os()} {platform_tools.host_arch()}"))

    for name, required in (("adb", True), ("fastboot", True), ("heimdall", False)):
        row, good = _tool_row(ctx, name, required)
        rows.append(row)
        ok = ok and good

    if ok:
        adb = ctx.adb()
        r = adb.start_server()
        rows.append(("adb server", "ok" if r.ok else "warn", r.err or "running"))
        devices = adb.devices()
        if not devices:
            rows.append(("devices", "warn", "none connected"))
        else:
            rows.append(("devices", "ok", ", ".join(f"{d.serial} ({d.state})" for d in devices)))
            if any(d.state == "unauthorized" for d in devices):
                rows.append(
                    ("authorization", "warn", "accept the USB debugging prompt on the phone")
                )

    host = platform_tools.host_os()
    if host == "linux":
        rules = glob.glob("/etc/udev/rules.d/*android*") + glob.glob("/lib/udev/rules.d/*android*")
        if rules:
            rows.append(("udev rules", "ok", rules[0]))
        else:
            rows.append(
                (
                    "udev rules",
                    "warn",
                    "no android udev rules; install android-sdk-platform-tools-common "
                    "or add a rule for your vendor id",
                )
            )
    elif host == "windows":
        rows.append(
            (
                "usb driver",
                "warn",
                "if the device is missing in adb devices install Google USB Driver "
                "or the vendor driver, then unplug and replug",
            )
        )
    elif host == "darwin":
        rows.append(("usb", "ok", f"macOS {platform.mac_ver()[0]}"))
    return rows, ok


def run(ctx: AppContext) -> None:
    rows, ok = collect(ctx)
    if ctx.json:
        print(json.dumps([{"check": n, "status": s, "detail": d} for n, s, d in rows], indent=2))
    else:
        ctx.console.print(doctor_table(rows))
    if not ok:
        raise ToolMissingError("required tools missing", hint="See failed rows above.")
