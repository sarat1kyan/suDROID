from __future__ import annotations

from sudroid.device.model import Device, Vendor
from sudroid.device.profiles.base import Quirk, VendorProfile


class XiaomiProfile(VendorProfile):
    name = "Xiaomi / Redmi / POCO"
    vendor = Vendor.XIAOMI
    unlock_automatable = False
    unlock_url = "https://en.miui.com/unlock/"

    def unlock_steps(self, d: Device) -> list[str]:
        return [
            "Sign in to a Mi account on the phone (Settings > Mi Account)",
            "Developer options > Mi Unlock status > Add account and device "
            "(needs mobile data, not WiFi)",
            "Wait the account binding period "
            "(72 hours to 30 days depending on region and HyperOS version)",
            "On a Windows PC install Mi Unlock Tool, sign in with the same Mi account",
            "Power off, hold Volume Down + Power to enter fastboot, connect, click Unlock",
            "Device wipes. Re-enable USB debugging, then run sudroid root",
        ]

    def unlock_commands(self, d: Device) -> list[list[str]]:
        return []

    def quirks(self, d: Device) -> list[Quirk]:
        q = super().quirks(d)
        q.append(
            Quirk(
                "mi-unlock",
                "Xiaomi unlock is account-bound and only possible through Mi Unlock Tool on "
                "Windows. The tool cannot automate it.",
                "warn",
            )
        )
        if d.sdk >= 34:
            q.append(
                Quirk(
                    "hyperos",
                    "HyperOS: unlock quota and community level requirements apply for "
                    "China ROM. Global ROMs are usually unrestricted.",
                )
            )
        return q
