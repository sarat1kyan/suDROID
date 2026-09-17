from __future__ import annotations

from sudroid.device.model import Device, Vendor
from sudroid.device.profiles.base import VendorProfile


class GenericProfile(VendorProfile):
    name = "Generic fastboot"
    vendor = Vendor.GENERIC

    def unlock_steps(self, d: Device) -> list[str]:
        return [
            "Enable OEM unlocking and USB debugging",
            "Tool reboots to bootloader and tries: fastboot flashing unlock, "
            "then fastboot oem unlock",
            "If both fail the vendor needs a token or tool. See quirks for chipset hints.",
        ]
