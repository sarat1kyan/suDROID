from __future__ import annotations

from sudroid.device.model import Device, Vendor
from sudroid.device.profiles.base import Quirk, VendorProfile


class SonyProfile(VendorProfile):
    name = "Sony Xperia"
    vendor = Vendor.SONY
    unlock_url = "https://developer.sony.com/open-source/aosp-on-xperia-open-devices/get-started/unlock-bootloader"

    def unlock_steps(self, d: Device) -> list[str]:
        return [
            "Dial *#*#7378423#*#* > Service info > Configuration: "
            "confirm 'Bootloader unlock allowed: Yes'",
            "Enable OEM unlocking and USB debugging",
            "Get IMEI (Settings > About phone) and request the unlock code "
            "on the Sony developer site",
            "Tool reboots to bootloader and runs: fastboot oem unlock 0x<CODE>. Device wipes.",
        ]

    def unlock_commands(self, d: Device) -> list[list[str]]:
        return []

    def needs_unlock_data(self, d: Device) -> bool:
        return True

    def unlock_data_command(self, d: Device) -> list[str] | None:
        return None

    def unlock_command_with_key(self, d: Device, key: str) -> list[str]:
        code = key if key.lower().startswith("0x") else f"0x{key}"
        return ["oem", "unlock", code]

    def quirks(self, d: Device) -> list[Quirk]:
        q = super().quirks(d)
        q.append(
            Quirk(
                "drm-keys",
                "Unlocking permanently erases Sony DRM keys (camera post-processing, "
                "some display features). This cannot be undone.",
                "warn",
            )
        )
        return q
