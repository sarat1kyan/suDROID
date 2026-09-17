from __future__ import annotations

from sudroid.device.model import Device, PatchTarget, Vendor
from sudroid.device.profiles.base import Quirk, VendorProfile


class GoogleProfile(VendorProfile):
    name = "Google Pixel"
    vendor = Vendor.GOOGLE
    unlock_url = "https://source.android.com/docs/setup/build/running#unlocking-the-bootloader"

    def unlock_steps(self, d: Device) -> list[str]:
        return [
            "Settings > About phone > tap Build number 7 times",
            "Settings > System > Developer options > enable OEM unlocking",
            "Enable USB debugging, connect, accept the RSA prompt",
            "Tool reboots to bootloader and runs: fastboot flashing unlock",
            "Confirm on the phone with the volume keys, then power. Device wipes.",
        ]

    def unlock_commands(self, d: Device) -> list[list[str]]:
        return [["flashing", "unlock"]]

    def patch_target(self, d: Device) -> PatchTarget:
        # Pixel 7 and later (first API 33) ship init_boot; Magisk goes there.
        return PatchTarget.INIT_BOOT if d.has_init_boot else PatchTarget.BOOT

    def quirks(self, d: Device) -> list[Quirk]:
        q = super().quirks(d)
        if d.oem_unlock_allowed is False and not d.is_unlocked:
            q.append(
                Quirk(
                    "oem-toggle",
                    "OEM unlocking is off. Carrier-locked Pixels (Verizon) cannot enable it.",
                    "warn",
                )
            )
        if self.patch_target(d) is PatchTarget.INIT_BOOT:
            q.append(
                Quirk(
                    "init-boot",
                    "init_boot target: fastboot boot test-boot is not possible, "
                    "the tool flashes directly after backup.",
                )
            )
        return q
