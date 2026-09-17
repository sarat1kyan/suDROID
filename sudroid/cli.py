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


@app.command()
def root(
    ctx: typer.Context,
    method: Annotated[str, typer.Option("--method", help="magisk (automated).")] = "magisk",
    image: Annotated[
        Path | None, typer.Option("--image", help="Stock boot/init_boot image for this build.")
    ] = None,
    no_test_boot: Annotated[
        bool, typer.Option("--no-test-boot", help="Skip fastboot boot test before flashing.")
    ] = False,
    skip_backup: Annotated[
        bool, typer.Option("--skip-backup", help="Do not save stock image.")
    ] = False,
    resume: Annotated[
        bool, typer.Option("--resume", help="Continue the last incomplete run.")
    ] = False,
    magisk_version: Annotated[
        str, typer.Option("--magisk-version", help="Pin a Magisk tag, e.g. v28.1.")
    ] = "",
) -> None:
    """Root the device: acquire stock image, back up, patch, test-boot, flash, verify."""
    from sudroid.commands import root as cmd

    _run(
        ctx,
        lambda c: cmd.run(
            c,
            method=method,
            image=image,
            no_test_boot=no_test_boot,
            skip_backup=skip_backup,
            resume=resume,
            magisk_version=magisk_version,
        ),
    )


@app.command()
def backup(
    ctx: typer.Context,
    image: Annotated[Path | None, typer.Option("--image", help="Stock image to register.")] = None,
    partition: Annotated[
        str | None, typer.Option("--partition", help="boot, init_boot or vendor_boot.")
    ] = None,
    list_only: Annotated[
        bool, typer.Option("--list", help="List backups for this device.")
    ] = False,
) -> None:
    """Save a stock image for this device, or list backups."""
    from sudroid.commands import backup as cmd

    _run(ctx, lambda c: cmd.run(c, image=image, partition=partition, list_only=list_only))


@app.command()
def patch(
    ctx: typer.Context,
    image: Annotated[Path, typer.Argument(help="Stock boot or init_boot image.")],
    out: Annotated[Path | None, typer.Option("--out", help="Output path.")] = None,
    magisk_version: Annotated[str, typer.Option("--magisk-version", help="Pin a Magisk tag.")] = "",
) -> None:
    """Patch an image with Magisk on the connected device. Nothing is flashed."""
    from sudroid.commands import patch as cmd

    _run(ctx, lambda c: cmd.run(c, image, out=out, magisk_version=magisk_version))


@app.command()
def flash(
    ctx: typer.Context,
    image: Annotated[Path, typer.Argument(help="Image to flash.")],
    partition: Annotated[
        str | None, typer.Option("--partition", help="boot, init_boot, vendor_boot, vbmeta.")
    ] = None,
    slot: Annotated[str, typer.Option("--slot", help="a, b or current.")] = "current",
    test_boot: Annotated[
        bool, typer.Option("--test-boot", help="fastboot boot the image first (boot only).")
    ] = False,
) -> None:
    """Flash a user supplied image (APatch, KernelSU, restore) to the right partition and slot."""
    from sudroid.commands import flash as cmd

    _run(ctx, lambda c: cmd.run(c, image, partition=partition, slot=slot, test_boot=test_boot))


@app.command()
def unlock(
    ctx: typer.Context,
    i_know: Annotated[
        bool, typer.Option("--i-know", help="Proceed without a stock image backup.")
    ] = False,
) -> None:
    """Unlock the bootloader. Wipes the device. Guided where the vendor needs a tool."""
    from sudroid.commands import unlock as cmd

    _run(ctx, lambda c: cmd.run(c, i_know=i_know))


@app.command()
def verify(ctx: typer.Context) -> None:
    """Check root access and which root solution is active."""
    from sudroid.commands import verify as cmd

    _run(ctx, cmd.run)


@app.command()
def restore(
    ctx: typer.Context,
    partition: Annotated[str | None, typer.Option("--partition")] = None,
    backup_id: Annotated[
        str | None, typer.Option("--backup", help="Backup id from --list.")
    ] = None,
) -> None:
    """Flash the saved stock image back."""
    from sudroid.commands import restore as cmd

    _run(ctx, lambda c: cmd.run(c, partition=partition, backup_id=backup_id))


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
