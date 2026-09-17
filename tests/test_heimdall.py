from pathlib import Path

from sudroid.tools.base import DryRunRunner, FakeRunner, Result
from sudroid.tools.heimdall import HeimdallClient


def test_detect_and_pit() -> None:
    fk = FakeRunner()
    fk.on(("heimdall", "detect"), lambda a: Result(a, 0, "Device detected", "", 0.0))
    fk.on(
        ("heimdall", "print-pit", "--no-reboot"),
        "Entry Count: 3\n--- Entry #0 ---\nPartition Name: BOOT\n--- Entry #1 ---\n"
        "Partition Name: INIT_BOOT\n--- Entry #2 ---\nPartition Name: VBMETA\n",
    )
    h = HeimdallClient(fk)
    assert h.detect()
    assert h.print_pit() == ["BOOT", "INIT_BOOT", "VBMETA"]


def test_detect_false_when_missing() -> None:
    fk = FakeRunner({("heimdall", "detect"): lambda a: Result(a, 1, "", "Failed to detect", 0.0)})
    assert HeimdallClient(fk).detect() is False


def test_flash_args_and_mutating() -> None:
    dry = DryRunRunner(FakeRunner())
    HeimdallClient(dry).flash({"BOOT": Path("b.img"), "VBMETA": Path("v.img")}, no_reboot=True)
    assert dry.recorded == [
        ("heimdall", "flash", "--BOOT", "b.img", "--VBMETA", "v.img", "--no-reboot")
    ]
