from pathlib import Path

from sudroid.tools.adb import AdbClient, AdbDevice
from sudroid.tools.base import DryRunRunner, FakeRunner, Result


def test_devices_parsing() -> None:
    fake = FakeRunner(
        {("adb", "devices"): "List of devices attached\nabc123\tdevice\nzzz\tunauthorized\n\n"}
    )
    adb = AdbClient(fake)
    assert adb.devices() == [AdbDevice("abc123", "device"), AdbDevice("zzz", "unauthorized")]
    assert adb.devices()[0].ready and not adb.devices()[1].ready


def test_serial_injected() -> None:
    fake = FakeRunner({("adb", "-s", "abc", "shell", "getprop"): "[ro.a]: [1]\n"})
    adb = AdbClient(fake, serial="abc")
    assert adb.getprop_all()["ro.a"] == "1"


def test_list_byname_and_failure() -> None:
    fake = FakeRunner()
    fake.on_prefix(("adb", "shell", "ls /dev/block/by-name"), "boot_a boot_b\ninit_boot_a\n")
    assert AdbClient(fake).list_byname() == frozenset({"boot_a", "boot_b", "init_boot_a"})
    fake2 = FakeRunner()
    fake2.on_prefix(
        ("adb", "shell", "ls /dev/block/by-name"),
        lambda a: Result(a, 1, "", "Permission denied", 0.0),
    )
    assert AdbClient(fake2).list_byname() == frozenset()


def test_which_and_battery() -> None:
    fake = FakeRunner()
    fake.on_prefix(("adb", "shell", "command -v magisk"), "yes\n")
    fake.on_prefix(("adb", "shell", "command -v ksud"), "no\n")
    fake.on(("adb", "shell", "dumpsys battery"), "Current Battery Service state:\n  level: 83\n")
    adb = AdbClient(fake)
    assert adb.which("magisk") is True
    assert adb.which("ksud") is False
    assert adb.battery_level() == 83


def test_mutating_ops_recorded_in_dry_run() -> None:
    fake = FakeRunner()
    dry = DryRunRunner(fake)
    adb = AdbClient(dry)
    adb.push(Path("x.img"), "/sdcard/x.img")
    adb.install(Path("app.apk"))
    adb.reboot("bootloader")
    assert dry.recorded == [
        ("adb", "push", "x.img", "/sdcard/x.img"),
        ("adb", "install", "-r", "app.apk"),
        ("adb", "reboot", "bootloader"),
    ]
    assert fake.calls == []


def test_root_shell_quotes() -> None:
    fake = FakeRunner()
    fake.on_prefix(("adb", "shell"), "uid=0(root)")
    adb = AdbClient(fake)
    r = adb.root_shell("id -u")
    assert r.text == "uid=0(root)"
    assert fake.calls[0] == ("adb", "shell", "su -c 'id -u'")
