from __future__ import annotations

from sudroid.device.model import Device, Vendor
from sudroid.device.profiles.asus import AsusProfile
from sudroid.device.profiles.base import VendorProfile
from sudroid.device.profiles.generic import GenericProfile
from sudroid.device.profiles.google import GoogleProfile
from sudroid.device.profiles.motorola import MotorolaProfile
from sudroid.device.profiles.nothing import NothingProfile
from sudroid.device.profiles.oneplus import OnePlusProfile
from sudroid.device.profiles.samsung import SamsungProfile
from sudroid.device.profiles.sony import SonyProfile
from sudroid.device.profiles.xiaomi import XiaomiProfile

_PROFILES: list[VendorProfile] = [
    GoogleProfile(),
    SamsungProfile(),
    XiaomiProfile(),
    OnePlusProfile(),
    MotorolaProfile(),
    SonyProfile(),
    AsusProfile(),
    NothingProfile(),
    GenericProfile(),
]

_BY_VENDOR: dict[Vendor, VendorProfile] = {p.vendor: p for p in _PROFILES}


def all_profiles() -> list[VendorProfile]:
    return list(_PROFILES)


def profile_for(d: Device) -> VendorProfile:
    return _BY_VENDOR.get(d.vendor, _BY_VENDOR[Vendor.GENERIC])
