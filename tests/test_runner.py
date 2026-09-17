import sys

import pytest

from sudroid.tools.base import DryRunRunner, FakeRunner, Result, SubprocessRunner


def test_subprocess_runner_captures_output() -> None:
    r = SubprocessRunner().run([sys.executable, "-c", "print(1)"])
    assert r.ok
    assert r.text == "1"
    assert r.returncode == 0
    assert r.duration >= 0


def test_subprocess_runner_nonzero_not_ok() -> None:
    r = SubprocessRunner().run([sys.executable, "-c", "import sys; sys.exit(3)"])
    assert not r.ok
    assert r.returncode == 3


def test_subprocess_runner_missing_binary() -> None:
    r = SubprocessRunner().run(["definitely-not-a-binary-xyz"])
    assert not r.ok
    assert r.returncode == 127
    assert "not found" in r.stderr


def test_result_text_normalizes_crlf() -> None:
    r = Result(("x",), 0, "a\r\nb\r\n", "", 0.0)
    assert r.text == "a\nb"


def test_dry_run_passes_reads_and_records_writes() -> None:
    inner = FakeRunner({("adb", "devices"): "List of devices attached\nabc\tdevice\n"})
    dry = DryRunRunner(inner)
    r = dry.run(["adb", "devices"])
    assert "abc" in r.text
    w = dry.run(["fastboot", "flash", "boot", "x.img"], mutating=True)
    assert w.ok
    assert dry.recorded == [("fastboot", "flash", "boot", "x.img")]
    assert inner.calls == [("adb", "devices")]


def test_fake_runner_unknown_command_raises() -> None:
    fake = FakeRunner({})
    with pytest.raises(KeyError, match="adb devices"):
        fake.run(["adb", "devices"])


def test_fake_runner_callable_response() -> None:
    fake = FakeRunner({("adb", "shell", "id"): lambda args: Result(args, 1, "", "denied", 0.0)})
    r = fake.run(["adb", "shell", "id"])
    assert r.returncode == 1
    assert r.stderr == "denied"


def test_fake_runner_prefix_match() -> None:
    fake = FakeRunner({})
    fake.on_prefix(("adb", "shell"), "ok")
    assert fake.run(["adb", "shell", "anything"]).text == "ok"
