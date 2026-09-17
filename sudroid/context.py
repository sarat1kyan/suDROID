"""Shared runtime context passed to every command."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console

from sudroid.config import Config
from sudroid.device.detect import detect
from sudroid.device.model import Device, RawInfo
from sudroid.errors import MultipleDevicesError, NoDeviceError, PreconditionError
from sudroid.tools import platform_tools
from sudroid.tools.adb import AdbClient, AdbDevice
from sudroid.tools.base import Runner
from sudroid.tools.fastboot import FastbootClient

log = logging.getLogger(__name__)


@dataclass
class AppContext:
    config: Config
    console: Console
    runner: Runner
    dry_run: bool = False
    json: bool = False
    yes: bool = False
    serial: str | None = None
    _adb: AdbClient | None = field(default=None, repr=False)
    _fastboot: FastbootClient | None = field(default=None, repr=False)

    def tool_path(self, name: str) -> Path:
        override = getattr(self.config.tools, name, "")
        return platform_tools.ensure(
            name, override=override, auto_download=self.config.tools.auto_download
        )

    def adb(self) -> AdbClient:
        if self._adb is None:
            self._adb = AdbClient(self.runner, str(self.tool_path("adb")), self.serial)
        return self._adb

    def fastboot(self) -> FastbootClient:
        if self._fastboot is None:
            self._fastboot = FastbootClient(
                self.runner, str(self.tool_path("fastboot")), self.serial
            )
        return self._fastboot


def pick_device(adb: AdbClient, serial: str | None) -> AdbDevice:
    devices = adb.devices()
    if serial:
        for d in devices:
            if d.serial == serial:
                return d
        raise NoDeviceError(f"device {serial} not found", hint="Check `adb devices`.")
    if not devices:
        raise NoDeviceError(
            "no device found",
            hint="Enable USB debugging, connect the phone, accept the RSA prompt.",
        )
    if len(devices) > 1:
        raise MultipleDevicesError(
            "multiple devices connected: " + ", ".join(d.serial for d in devices),
            hint="Pass --serial <id>.",
        )
    return devices[0]


def ensure_authorized(dev: AdbDevice) -> None:
    if dev.state == "unauthorized":
        raise PreconditionError(
            f"device {dev.serial} is unauthorized",
            hint="Unlock the phone and accept the USB debugging prompt.",
        )
    if dev.state != "device":
        raise PreconditionError(
            f"device {dev.serial} is in state {dev.state}",
            hint="Boot to Android with USB debugging enabled.",
        )


def gather(ctx: AppContext) -> RawInfo:
    """Collect raw facts from a booted device over adb."""
    adb = ctx.adb()
    dev = pick_device(adb, ctx.serial)
    ensure_authorized(dev)
    adb.serial = dev.serial
    props = adb.getprop_all()
    byname = adb.list_byname()
    which = {name: adb.which(name) for name in ("magisk", "ksud", "apd", "su")}
    battery = adb.battery_level()
    kernel = adb.shell("uname -r", timeout=15).text.strip()
    return RawInfo(props=props, byname=byname, which=which, battery=battery, kernel=kernel)


def gather_fastboot(ctx: AppContext) -> RawInfo:
    """Collect facts when the device sits in bootloader mode."""
    fb = ctx.fastboot()
    devices = fb.devices()
    if not devices:
        raise NoDeviceError("no fastboot device found")
    if ctx.serial is None and len(devices) > 1:
        raise MultipleDevicesError("multiple fastboot devices: " + ", ".join(devices))
    fb.serial = ctx.serial or devices[0]
    from sudroid.device.props import Props

    return RawInfo(props=Props(), fastboot_vars=fb.getvar_all())


def detect_device(ctx: AppContext) -> Device:
    return detect(gather(ctx))
