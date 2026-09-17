from pathlib import Path

from sudroid.tools.base import DryRunRunner, FakeRunner, Result
from sudroid.tools.fastboot import FastbootClient, parse_getvar

GETVAR_ALL = """(bootloader) current-slot:a
(bootloader) slot-count:2
(bootloader) has-slot:init_boot:yes
(bootloader) has-slot:boot:yes
(bootloader) unlocked:yes
(bootloader) serialno:ABC123
(bootloader) partition-type:init_boot_a:raw
all:
Finished. Total time: 0.050s
"""


def test_parse_getvar_all() -> None:
    v = parse_getvar(GETVAR_ALL)
    assert v["current-slot"] == "a"
    assert v["slot-count"] == "2"
    assert v["has-slot:init_boot"] == "yes"
    assert v["unlocked"] == "yes"
    assert v["partition-type:init_boot_a"] == "raw"
    assert "Finished" not in v


def test_getvar_from_stderr() -> None:
    fake = FakeRunner(
        {
            ("fastboot", "getvar", "unlocked"): lambda a: Result(
                a, 0, "", "unlocked: no\r\nFinished. Total time: 0.001s\r\n", 0.0
            )
        }
    )
    fb = FastbootClient(fake)
    assert fb.getvar("unlocked") == "no"
    assert fb.unlocked() is False


def test_current_slot_strips_underscore() -> None:
    fake = FakeRunner(
        {
            ("fastboot", "getvar", "current-slot"): lambda a: Result(
                a, 0, "", "current-slot: _b\n", 0.0
            )
        }
    )
    assert FastbootClient(fake).current_slot() == "b"


def test_devices() -> None:
    fake = FakeRunner({("fastboot", "devices"): "ABC123\tfastboot\nXYZ\tfastbootd\n"})
    assert FastbootClient(fake).devices() == ["ABC123", "XYZ"]


def test_mutating_ops_dry_run() -> None:
    fake = FakeRunner()
    dry = DryRunRunner(fake)
    fb = FastbootClient(dry, serial="S1")
    fb.flash("init_boot_a", Path("p.img"))
    fb.boot(Path("p.img"))
    fb.flashing("unlock")
    fb.oem("unlock", "KEY")
    fb.reboot()
    assert dry.recorded == [
        ("fastboot", "-s", "S1", "flash", "init_boot_a", "p.img"),
        ("fastboot", "-s", "S1", "boot", "p.img"),
        ("fastboot", "-s", "S1", "flashing", "unlock"),
        ("fastboot", "-s", "S1", "oem", "unlock", "KEY"),
        ("fastboot", "-s", "S1", "reboot"),
    ]


def test_oem_read_is_not_mutating() -> None:
    fake = FakeRunner()
    fake.on(
        ("fastboot", "oem", "get_unlock_data"),
        lambda a: Result(a, 0, "", "(bootloader) 0A40...\n", 0.0),
    )
    dry = DryRunRunner(fake)
    r = FastbootClient(dry).oem_read("get_unlock_data")
    assert "0A40" in r.err
    assert dry.recorded == []
