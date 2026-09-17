"""Command line entry point."""

from __future__ import annotations

import typer

import sudroid

app = typer.Typer(name="sudroid", help="Android rooting toolkit.", no_args_is_help=True)


@app.command()
def version() -> None:
    """Print version."""
    typer.echo(sudroid.__version__)
