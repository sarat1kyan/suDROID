from __future__ import annotations

from sudroid.device.model import Device, Vendor
from sudroid.device.profiles.base import Quirk, VendorProfile


class OnePlusProfile(VendorProfile):
    name = "OnePlus"
    vendor = Vendor.ONEPLUS

    def unlock_steps(self, d: Device) -> list[str]:
        return [
            "Settings > About device > tap Build number 7 times",
            "Developer options > enable OEM unlocking and USB debugging",
            "Tool reboots to bootloader and runs: fastboot oem unlock",
            "Confirm UNLOCK THE BOOTLOADER on the phone. Device wipes.",
        ]

    def unlock_commands(self, d: Device) -> list[list[str]]:
        return [["oem", "unlock"], ["flashing", "unlock"]]

    def quirks(self, d: Device) -> list[Quirk]:
        q = super().quirks(d)
        if d.sdk >= 34:
            q.append(
                Quirk(
                    "oos14",
                    "OxygenOS 14 and later: stock boot images are only in full OTA payloads. "
                    "Use --firmware with the OTA zip.",
                )
            )
        return q
