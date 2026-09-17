from __future__ import annotations

from sudroid.device.model import Device, PatchTarget, Vendor
from sudroid.device.profiles.base import VendorProfile


class NothingProfile(VendorProfile):
    name = "Nothing"
    vendor = Vendor.NOTHING

    def unlock_steps(self, d: Device) -> list[str]:
        return [
            "Enable OEM unlocking and USB debugging",
            "Tool reboots to bootloader and runs: fastboot flashing unlock",
            "Confirm on the phone. Device wipes.",
        ]

    def unlock_commands(self, d: Device) -> list[list[str]]:
        return [["flashing", "unlock"]]

    def patch_target(self, d: Device) -> PatchTarget:
        if d.first_api_level >= 33 or d.has_init_boot:
            return PatchTarget.INIT_BOOT
        return PatchTarget.BOOT
