"""Vendor profile contract. All vendor-specific behavior lives in this package."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from sudroid.device.model import Device, FlashBackend, PatchTarget, SocVendor, Vendor


@dataclass(frozen=True)
class Quirk:
    code: str
    message: str
    severity: str = "info"  # info, warn, block


class VendorProfile(ABC):
    name: str = ""
    vendor: Vendor = Vendor.GENERIC
    flash_backend: FlashBackend = FlashBackend.FASTBOOT
    supports_test_boot: bool = True
    unlock_wipes_data: bool = True
    unlock_automatable: bool = True
    unlock_url: str = ""

    @abstractmethod
    def unlock_steps(self, d: Device) -> list[str]:
        """Human steps to unlock the bootloader, in order."""

    def unlock_commands(self, d: Device) -> list[list[str]]:
        """Fastboot argument lists to try in order. Empty when not automatable."""
        return [["flashing", "unlock"], ["oem", "unlock"]]

    def needs_unlock_data(self, d: Device) -> bool:
        """True when the tool must first read data from the device (Motorola, Sony)."""
        return False

    def unlock_data_command(self, d: Device) -> list[str] | None:
        return None

    def unlock_command_with_key(self, d: Device, key: str) -> list[str] | None:
        return None

    def patch_target(self, d: Device) -> PatchTarget:
        return d.patch_target

    def quirks(self, d: Device) -> list[Quirk]:
        return list(soc_quirks(d))

    def flash_partition(self, d: Device, target: PatchTarget) -> str:
        return f"{target.value}{d.slot_suffix}"


def soc_quirks(d: Device) -> list[Quirk]:
    out: list[Quirk] = []
    if d.soc is SocVendor.MEDIATEK:
        out.append(
            Quirk(
                "mtk",
                "MediaTek SoC. If the vendor offers no unlock path, mtkclient "
                "(https://github.com/bkerler/mtkclient) can unlock via BROM on many models.",
            )
        )
    if d.soc is SocVendor.UNISOC:
        out.append(
            Quirk(
                "unisoc",
                "Unisoc SoC. Bootloader unlock usually needs a signed identifier token "
                "from the vendor. Community tooling: "
                "https://github.com/TomKing062/CVE-2022-38694_unlock_bootloader",
            )
        )
    if d.dynamic_partitions is False and d.sdk >= 29:
        out.append(Quirk("no-dynparts", "No dynamic partitions reported; older layout."))
    return out
