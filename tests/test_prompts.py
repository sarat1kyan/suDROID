import pytest
from rich.console import Console

from sudroid.config import Config
from sudroid.context import AppContext
from sudroid.errors import UserAbortError
from sudroid.tools.base import FakeRunner
from sudroid.ui import prompts


def ctx(yes: bool) -> AppContext:
    return AppContext(Config(), Console(quiet=True), FakeRunner(), yes=yes)


def test_confirm_yes_flag() -> None:
    assert prompts.confirm(ctx(True), "q") is True


def test_confirm_reads_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(prompts.Prompt, "ask", staticmethod(lambda *a, **k: "y"))
    assert prompts.confirm(ctx(False), "q") is True
    monkeypatch.setattr(prompts.Prompt, "ask", staticmethod(lambda *a, **k: ""))
    assert prompts.confirm(ctx(False), "q", default=True) is True
    assert prompts.confirm(ctx(False), "q") is False


def test_typed_confirm_not_bypassed_by_yes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(prompts.Prompt, "ask", staticmethod(lambda *a, **k: "nope"))
    with pytest.raises(UserAbortError):
        prompts.typed_confirm(ctx(True), "UNLOCK", "warning")
    monkeypatch.setattr(prompts.Prompt, "ask", staticmethod(lambda *a, **k: "UNLOCK"))
    prompts.typed_confirm(ctx(True), "UNLOCK", "warning")
