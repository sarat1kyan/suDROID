from __future__ import annotations

from sudroid.device.model import Device, Vendor
from sudroid.device.profiles.base import Quirk, VendorProfile


class AsusProfile(VendorProfile):
    name = "ASUS"
    vendor = Vendor.ASUS
    unlock_automatable = False

    def unlock_steps(self, d: Device) -> list[str]:
        return [
            "Enable OEM unlocking and USB debugging",
            "Install the ASUS Unlock Device App for your model from the ASUS support site "
            "(ROG Phone and Zenfone). Older models accept fastboot flashing unlock",
            "Run the app, accept the warranty void notice. Device wipes",
        ]

    def unlock_commands(self, d: Device) -> list[list[str]]:
        return [["flashing", "unlock"], ["oem", "unlock"]]

    def quirks(self, d: Device) -> list[Quirk]:
        q = super().quirks(d)
        q.append(
            Quirk(
                "asus-app",
                "ASUS discontinued the unlock app for several models in 2023. "
                "Check availability before buying into this path.",
                "warn",
            )
        )
        return q
