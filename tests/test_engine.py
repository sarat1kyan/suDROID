from pathlib import Path

import pytest
from rich.console import Console

from sudroid.config import Config
from sudroid.context import AppContext
from sudroid.device.detect import detect
from sudroid.device.model import RawInfo
from sudroid.device.profiles import profile_for
from sudroid.device.props import Props
from sudroid.errors import PreconditionError, UserAbortError
from sudroid.tools.base import FakeRunner
from sudroid.ui import prompts
from sudroid.workflow import session as sm
from sudroid.workflow.engine import Engine, Runtime, Step
from tests.conftest import getprop_text


class Rec(Step):
    def __init__(
        self, name: str, mutating: bool = False, fail: bool = False, skip: str = ""
    ) -> None:
        self.name = name
        self.title = name
        self.mutating = mutating
        self._fail = fail
        self._skip = skip
        self.ran = 0
        self.undone = 0

    def skip(self, rt: Runtime) -> str:
        return self._skip

    def run(self, rt: Runtime) -> None:
        self.ran += 1
        if self._fail:
            raise PreconditionError("boom")

    def undo(self, rt: Runtime) -> None:
        self.undone += 1


def make_rt(tmp_path: Path, *, yes: bool = True, dry: bool = False) -> Runtime:
    d = detect(RawInfo(props=Props.parse(getprop_text("pixel5"))))
    ctx = AppContext(Config(), Console(quiet=True), FakeRunner(), dry_run=dry, yes=yes)
    s = sm.new_session(d.serial, "root")
    return Runtime(ctx, d, profile_for(d), s, tmp_path / "work", session_root=tmp_path / "sessions")


def test_runs_all_and_checkpoints(tmp_path: Path) -> None:
    rt = make_rt(tmp_path)
    a, b, c = Rec("a"), Rec("b", mutating=True), Rec("c", skip="not needed")
    Engine(rt, [a, b, c]).run()
    assert (a.ran, b.ran, c.ran) == (1, 1, 0)
    assert rt.session.steps_done == ["a", "b", "c"]
    assert rt.session.status == "done"
    loaded = sm.load(rt.session.path(tmp_path / "sessions"))
    assert loaded.steps_done == ["a", "b", "c"]


def test_resume_skips_done(tmp_path: Path) -> None:
    rt = make_rt(tmp_path)
    rt.session.steps_done = ["a"]
    a, b = Rec("a"), Rec("b")
    Engine(rt, [a, b]).run()
    assert a.ran == 0 and b.ran == 1


def test_failure_marks_and_offers_undo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rt = make_rt(tmp_path, yes=False)
    answers = iter([True, True])  # confirm mutating step, confirm undo
    monkeypatch.setattr(prompts, "confirm", lambda ctx, q, default=False: next(answers))
    a, b = Rec("a", mutating=True), Rec("b", fail=True)
    with pytest.raises(PreconditionError):
        Engine(rt, [a, b]).run()
    assert rt.session.status == "failed"
    assert a.undone == 1
    assert rt.session.steps_done == ["a"]


def test_user_decline_aborts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rt = make_rt(tmp_path, yes=False)
    monkeypatch.setattr(prompts, "confirm", lambda ctx, q, default=False: False)
    a = Rec("a", mutating=True)
    with pytest.raises(UserAbortError):
        Engine(rt, [a]).run()
    assert a.ran == 0
    assert rt.session.status == "aborted"


def test_dry_run_runs_mutating_step_without_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rt = make_rt(tmp_path, yes=False, dry=True)
    monkeypatch.setattr(prompts, "confirm", lambda *a, **k: pytest.fail("no prompt in dry-run"))
    a = Rec("a", mutating=True)
    Engine(rt, [a]).run()
    assert a.ran == 1  # step runs; the runner blocks actual writes


def test_plan_table_states(tmp_path: Path) -> None:
    rt = make_rt(tmp_path)
    rt.session.steps_done = ["a"]
    t = Engine(rt, [Rec("a"), Rec("b", skip="x"), Rec("c", mutating=True)]).plan_table()
    assert t.row_count == 3


def test_latest_incomplete(tmp_path: Path) -> None:
    root = tmp_path / "s"
    s1 = sm.new_session("SER", "root")
    s1.status = "done"
    sm.save(s1, root)
    s2 = sm.new_session("SER", "root")
    s2.id = "zzz-later"
    s2.status = "failed"
    sm.save(s2, root)
    got = sm.latest_incomplete("SER", "root", root)
    assert got is not None and got.id == "zzz-later"
    assert sm.latest_incomplete("SER", "flash", root) is None
