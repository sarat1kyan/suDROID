"""Step engine: check, confirm, run, checkpoint, undo on failure."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from rich.table import Table

from sudroid.context import AppContext
from sudroid.device.model import Device
from sudroid.device.profiles.base import VendorProfile
from sudroid.errors import SudroidError, UserAbortError
from sudroid.ui import prompts
from sudroid.workflow import session as session_mod
from sudroid.workflow.session import Session

log = logging.getLogger(__name__)


@dataclass
class Runtime:
    ctx: AppContext
    device: Device
    profile: VendorProfile
    session: Session
    work: Path
    session_root: Path | None = None
    data: dict[str, str] = field(default_factory=dict)

    def save(self) -> None:
        self.session.data = dict(self.data)
        session_mod.save(self.session, self.session_root)

    def say(self, msg: str) -> None:
        self.ctx.console.print(msg)


class Step(ABC):
    name: str = ""
    title: str = ""
    mutating: bool = False

    def skip(self, rt: Runtime) -> str:
        """Return a reason to skip this step, or empty string."""
        return ""

    def check(self, rt: Runtime) -> None:
        return None

    @abstractmethod
    def run(self, rt: Runtime) -> None: ...

    def undo(self, rt: Runtime) -> None:
        return None

    def describe(self, rt: Runtime) -> str:
        return self.title


class Engine:
    def __init__(self, rt: Runtime, steps: list[Step]) -> None:
        self.rt = rt
        self.steps = steps

    def plan_table(self) -> Table:
        t = Table(title="Plan")
        t.add_column("#", justify="right")
        t.add_column("Step")
        t.add_column("Writes", justify="center")
        t.add_column("State")
        for i, s in enumerate(self.steps, 1):
            if s.name in self.rt.session.steps_done:
                state = "done"
            else:
                reason = s.skip(self.rt)
                state = f"skip: {reason}" if reason else ""
            t.add_row(str(i), s.describe(self.rt), "yes" if s.mutating else "", state)
        return t

    def run(self) -> None:
        rt = self.rt
        done_mutating: list[Step] = []
        try:
            for step in self.steps:
                if step.name in rt.session.steps_done:
                    log.info("skip %s (already done)", step.name)
                    continue
                reason = step.skip(rt)
                if reason:
                    rt.say(f"[dim]skip {step.title}: {reason}[/]")
                    rt.session.steps_done.append(step.name)
                    rt.save()
                    continue
                step.check(rt)
                if step.mutating:
                    if rt.ctx.dry_run:
                        rt.say(f"[yellow]dry-run:[/] would run {step.describe(rt)}")
                    else:
                        prompts.require(rt.ctx, f"{step.describe(rt)}. Continue?")
                rt.say(f"[bold]{step.title}[/]")
                step.run(rt)
                if step.mutating:
                    done_mutating.append(step)
                rt.session.steps_done.append(step.name)
                rt.save()
            rt.session.status = "done"
            rt.save()
        except UserAbortError:
            rt.session.status = "aborted"
            rt.save()
            raise
        except (SudroidError, Exception) as exc:
            rt.session.status = "failed"
            rt.save()
            log.error("step failed: %s", exc)
            self._offer_undo(done_mutating)
            raise

    def _offer_undo(self, done_mutating: list[Step]) -> None:
        undoable = [s for s in reversed(done_mutating) if type(s).undo is not Step.undo]
        if not undoable or self.rt.ctx.dry_run:
            return
        names = ", ".join(s.title for s in undoable)
        if prompts.confirm(self.rt.ctx, f"Undo completed steps ({names})?", default=False):
            for s in undoable:
                try:
                    self.rt.say(f"[yellow]undo {s.title}[/]")
                    s.undo(self.rt)
                except Exception as exc:  # noqa: BLE001
                    log.error("undo %s failed: %s", s.name, exc)
