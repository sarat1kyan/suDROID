from __future__ import annotations

from sudroid.device.model import Device, FlashBackend, PatchTarget, Vendor
from sudroid.device.profiles.base import Quirk, VendorProfile


class SamsungProfile(VendorProfile):
    name = "Samsung Galaxy"
    vendor = Vendor.SAMSUNG
    flash_backend = FlashBackend.HEIMDALL
    supports_test_boot = False
    unlock_automatable = False

    def unlock_steps(self, d: Device) -> list[str]:
        return [
            "Developer options > enable OEM unlocking (if missing: set date back 7 days, "
            "toggle auto date off, or wait 7 days on fresh firmware, RMM/KG prenormal lock)",
            "Power off. Hold Volume Up + Volume Down and plug in USB to enter download mode",
            "Long press Volume Up on the warning screen to open the unlock menu",
            "Press Volume Up to unlock. Device wipes and reboots",
            "Complete setup, connect to WiFi, then confirm OEM unlocking is greyed on and "
            "'VaultKeeper' is satisfied by rebooting once with internet",
        ]

    def unlock_commands(self, d: Device) -> list[list[str]]:
        return []

    def patch_target(self, d: Device) -> PatchTarget:
        if d.first_api_level >= 33 or d.has_init_boot:
            return PatchTarget.INIT_BOOT
        return PatchTarget.BOOT

    def flash_partition(self, d: Device, target: PatchTarget) -> str:
        # Heimdall uses PIT partition names, upper case, no slot suffix.
        return target.value.upper()

    def quirks(self, d: Device) -> list[Quirk]:
        q = super().quirks(d)
        q.append(
            Quirk(
                "no-fastboot",
                "Samsung has no fastboot. Flashing uses Heimdall (download mode) or an Odin tar.",
            )
        )
        q.append(
            Quirk(
                "knox",
                "Flashing a patched image trips the Knox warranty bit permanently. "
                "Samsung Pay, Secure Folder and Knox features stop working.",
                "warn",
            )
        )
        q.append(
            Quirk(
                "us-models",
                "US carrier and Snapdragon variants (SM-xxxxU, U1, W) have no OEM unlocking; "
                "bootloader cannot be unlocked.",
                "warn",
            )
        )
        if d.model.upper().endswith(("U", "U1", "W")):
            q.append(
                Quirk("us-variant", f"{d.model} looks like a US variant. Unlock blocked.", "block")
            )
        if d.kg_locked and not d.is_unlocked:
            q.append(
                Quirk(
                    "kg",
                    "KG/RMM lock flag set. If OEM unlocking is missing in Developer options, "
                    "keep the SIM in with internet for 7 days and do not factory reset.",
                    "warn",
                )
            )
        if d.warranty_bit == "1":
            q.append(Quirk("knox-tripped", "Knox warranty bit already tripped."))
        return q
