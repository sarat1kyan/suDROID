"""Immutable device description. Everything downstream reads from this."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum

from sudroid.device.props import Props


class Vendor(str, Enum):
    GOOGLE = "google"
    SAMSUNG = "samsung"
    XIAOMI = "xiaomi"
    ONEPLUS = "oneplus"
    MOTOROLA = "motorola"
    SONY = "sony"
    ASUS = "asus"
    NOTHING = "nothing"
    GENERIC = "generic"


class SocVendor(str, Enum):
    QUALCOMM = "qualcomm"
    MEDIATEK = "mediatek"
    EXYNOS = "exynos"
    TENSOR = "tensor"
    UNISOC = "unisoc"
    UNKNOWN = "unknown"


class LockState(str, Enum):
    LOCKED = "locked"
    UNLOCKED = "unlocked"
    UNKNOWN = "unknown"


class PatchTarget(str, Enum):
    BOOT = "boot"
    INIT_BOOT = "init_boot"


class FlashBackend(str, Enum):
    FASTBOOT = "fastboot"
    HEIMDALL = "heimdall"
    ODIN_TAR = "odin_tar"


@dataclass(frozen=True)
class RawInfo:
    """Everything collected from the device before interpretation."""

    props: Props
    byname: frozenset[str] = frozenset()
    fastboot_vars: Mapping[str, str] = field(default_factory=dict)
    which: Mapping[str, bool] = field(default_factory=dict)
    battery: int | None = None


@dataclass(frozen=True)
class Device:
    serial: str
    model: str
    brand: str
    manufacturer: str
    codename: str
    android: str
    sdk: int
    first_api_level: int
    build_id: str
    fingerprint: str
    security_patch: str
    vendor: Vendor
    soc: SocVendor
    soc_model: str
    ab: bool
    slot: str
    has_init_boot: bool
    has_vendor_boot: bool
    dynamic_partitions: bool
    patch_target: PatchTarget
    lock: LockState
    oem_unlock_allowed: bool | None
    encryption: str
    root_present: str
    battery: int | None
    warranty_bit: str = ""
    kg_locked: bool = False
    init_boot_inferred: bool = False
    abi: str = ""

    @property
    def slot_suffix(self) -> str:
        return f"_{self.slot}" if self.slot else ""

    @property
    def is_unlocked(self) -> bool:
        return self.lock is LockState.UNLOCKED

    @property
    def display_name(self) -> str:
        return f"{self.brand} {self.model} ({self.codename})".strip()
