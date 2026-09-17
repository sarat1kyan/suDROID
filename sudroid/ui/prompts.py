"""User confirmations. typed_confirm is never bypassed by --yes."""

from __future__ import annotations

from rich.prompt import Prompt

from sudroid.context import AppContext
from sudroid.errors import UserAbortError


def confirm(ctx: AppContext, question: str, *, default: bool = False) -> bool:
    if ctx.yes:
        return True
    suffix = "[Y/n]" if default else "[y/N]"
    answer = Prompt.ask(f"{question} {suffix}", console=ctx.console, default="").strip().lower()
    if not answer:
        return default
    return answer in {"y", "yes"}


def require(ctx: AppContext, question: str) -> None:
    if not confirm(ctx, question):
        raise UserAbortError("aborted by user")


def typed_confirm(ctx: AppContext, word: str, warning: str) -> None:
    ctx.console.print(f"[bold red]{warning}[/]")
    answer = Prompt.ask(f"Type {word} to continue", console=ctx.console, default="")
    if answer.strip() != word:
        raise UserAbortError(f"confirmation word did not match ({word})")


def choose(ctx: AppContext, prompt: str, options: list[str], default: str | None = None) -> str:
    if ctx.yes and default is not None:
        return default
    if default is None:
        return Prompt.ask(prompt, choices=options, console=ctx.console)
    return Prompt.ask(prompt, choices=options, default=default, console=ctx.console)
