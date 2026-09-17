from __future__ import annotations

from pathlib import Path

from sudroid.context import AppContext, detect_device
from sudroid.device.profiles import profile_for
from sudroid.errors import PreconditionError
from sudroid.paths import data_dir
from sudroid.ui import prompts
from sudroid.ui.render import device_table, quirks_table
from sudroid.workflow import session as sm
from sudroid.workflow.engine import Engine, Runtime
from sudroid.workflow.steps import root_steps


def run(
    ctx: AppContext,
    *,
    method: str = "magisk",
    image: Path | None = None,
    no_test_boot: bool = False,
    skip_backup: bool = False,
    resume: bool = False,
    magisk_version: str = "",
    firmware: Path | None = None,
    odin: bool = False,
    auto_fetch: bool = False,
) -> None:
    method = method.lower()
    if method not in {"magisk", "kernelsu", "apatch"}:
        raise PreconditionError(f"unknown method {method}", hint="magisk, kernelsu or apatch")
    device = detect_device(ctx)
    profile = profile_for(device)
    ctx.console.print(device_table(device, profile))
    quirks = profile.quirks(device)
    if quirks:
        ctx.console.print(quirks_table(quirks))
    if any(q.severity == "block" for q in quirks):
        raise PreconditionError(
            "device profile blocks rooting", hint="; ".join(q.message for q in quirks)
        )

    session = sm.latest_incomplete(device.serial, "root") if resume else None
    if resume and session is None:
        ctx.console.print("[yellow]no incomplete session found, starting fresh[/]")
    if session is None:
        session = sm.new_session(device.serial, "root")
    else:
        ctx.console.print(f"resuming session {session.id} ({len(session.steps_done)} steps done)")
        session.status = "running"

    work = data_dir() / "work" / session.id
    rt = Runtime(ctx, device, profile, session, work)
    rt.data.update(session.data)
    if image:
        rt.data["image"] = str(image)
    if no_test_boot:
        rt.data["no_test_boot"] = "1"
    if skip_backup:
        rt.data["skip_backup"] = "1"
    if magisk_version:
        rt.data["magisk_version"] = magisk_version
    if firmware:
        rt.data["firmware"] = str(firmware)
    if odin:
        rt.data["odin"] = "1"
    if auto_fetch:
        rt.data["auto_fetch"] = "1"
    rt.data["method"] = method

    engine = Engine(rt, root_steps(profile, method))
    ctx.console.print(engine.plan_table())
    if not ctx.dry_run:
        prompts.require(ctx, "Start rooting?")
    engine.run()
    ctx.console.print(f"[green]done.[/] session {session.id}, work dir {work}")
