"""Command line entry point."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

import typer

import sudroid
from sudroid import config as config_mod
from sudroid import log as log_mod
from sudroid.context import AppContext
from sudroid.errors import SudroidError
from sudroid.tools.base import DryRunRunner, Runner, SubprocessRunner

app = typer.Typer(
    name="sudroid",
    help="Android rooting toolkit. Detect, back up, patch, test-boot, flash.",
    no_args_is_help=True,
    add_completion=False,
    rich_markup_mode="rich",
    pretty_exceptions_enable=False,
)

log = logging.getLogger("sudroid")


def _make_runner() -> Runner:
    return SubprocessRunner()


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(sudroid.__version__)
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Print device writes instead of executing them.")
    ] = False,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Assume yes on confirmations.")] = False,
    serial: Annotated[
        str | None, typer.Option("--serial", "-s", help="Target device serial.")
    ] = None,
    json_out: Annotated[bool, typer.Option("--json", help="Machine readable output.")] = False,
    log_level: Annotated[
        str | None, typer.Option("--log-level", help="debug, info, warning, error.")
    ] = None,
    config_path: Annotated[
        Path | None, typer.Option("--config", help="Path to config.toml.")
    ] = None,
    no_color: Annotated[bool, typer.Option("--no-color", help="Disable colors.")] = False,
    version: Annotated[
        bool | None,
        typer.Option("--version", callback=_version_callback, is_eager=True, help="Show version."),
    ] = None,
) -> None:
    cfg = config_mod.load(config_path)
    level = log_level or cfg.general.log_level
    console = log_mod.setup(level, json_mode=json_out, no_color=no_color)
    runner: Runner = _make_runner()
    if dry_run:
        runner = DryRunRunner(runner)
        console.print("[yellow]dry-run: device writes are printed, not executed[/]")
    ctx.obj = AppContext(
        config=cfg,
        console=console,
        runner=runner,
        dry_run=dry_run,
        json=json_out,
        yes=yes,
        serial=serial,
    )


def _run(ctx: typer.Context, fn: object) -> None:
    app_ctx: AppContext = ctx.obj
    try:
        fn(app_ctx)  # type: ignore[operator]
    except SudroidError as exc:
        app_ctx.console.print(f"[red]error:[/] {exc.message}")
        if exc.hint:
            app_ctx.console.print(f"[yellow]hint:[/] {exc.hint}")
        log.debug("failed", exc_info=exc)
        raise typer.Exit(code=exc.exit_code) from None
    except KeyboardInterrupt:
        app_ctx.console.print("[yellow]aborted[/]")
        raise typer.Exit(code=30) from None


@app.command()
def doctor(ctx: typer.Context) -> None:
    """Check host tools, drivers and adb server."""
    from sudroid.commands import doctor as cmd

    _run(ctx, cmd.run)


@app.command()
def info(ctx: typer.Context) -> None:
    """Show device report: vendor, SoC, slot, partitions, lock state, root."""
    from sudroid.commands import info as cmd

    _run(ctx, cmd.run)


@app.command()
def profiles(ctx: typer.Context) -> None:
    """List vendor profiles and support matrix."""
    from sudroid.commands import profiles as cmd

    _run(ctx, cmd.run)


@app.command("config")
def config_cmd(
    ctx: typer.Context,
    init: Annotated[bool, typer.Option("--init", help="Write a default config file.")] = False,
) -> None:
    """Show effective configuration."""
    import json as _json

    app_ctx: AppContext = ctx.obj
    if init:
        path = config_mod.write_default()
        app_ctx.console.print(f"wrote {path}")
        return
    app_ctx.console.print(f"config file: {config_mod.default_path()}")
    print(_json.dumps(app_ctx.config.to_dict(), indent=2))
