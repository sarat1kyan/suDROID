from __future__ import annotations

from sudroid.device.model import Device, Vendor
from sudroid.device.profiles.base import VendorProfile


class MotorolaProfile(VendorProfile):
    name = "Motorola"
    vendor = Vendor.MOTOROLA
    unlock_url = "https://en-us.support.motorola.com/app/standalone/bootloader/unlock-your-device-a"

    def unlock_steps(self, d: Device) -> list[str]:
        return [
            "Enable OEM unlocking and USB debugging in Developer options",
            "Tool reboots to bootloader and runs: fastboot oem get_unlock_data",
            "Paste the 5 lines (concatenated, no spaces) into the Motorola unlock page",
            "Motorola emails a 20 character unlock key",
            "Tool runs: fastboot oem unlock <KEY>. Device wipes.",
        ]

    def unlock_commands(self, d: Device) -> list[list[str]]:
        return []

    def needs_unlock_data(self, d: Device) -> bool:
        return True

    def unlock_data_command(self, d: Device) -> list[str]:
        return ["oem", "get_unlock_data"]

    def unlock_command_with_key(self, d: Device, key: str) -> list[str]:
        return ["oem", "unlock", key]
