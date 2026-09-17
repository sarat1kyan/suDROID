"""Pure detection: RawInfo -> Device. No I/O here."""

from __future__ import annotations

from collections.abc import Mapping

from sudroid.device.model import Device, LockState, PatchTarget, RawInfo, SocVendor, Vendor

_VENDOR_BY_MANUFACTURER: dict[str, Vendor] = {
    "google": Vendor.GOOGLE,
    "samsung": Vendor.SAMSUNG,
    "xiaomi": Vendor.XIAOMI,
    "oneplus": Vendor.ONEPLUS,
    "motorola": Vendor.MOTOROLA,
    "sony": Vendor.SONY,
    "asus": Vendor.ASUS,
    "nothing": Vendor.NOTHING,
}

_VENDOR_BY_BRAND: dict[str, Vendor] = {
    "redmi": Vendor.XIAOMI,
    "poco": Vendor.XIAOMI,
    "xiaomi": Vendor.XIAOMI,
    "motorola": Vendor.MOTOROLA,
    "moto": Vendor.MOTOROLA,
    "google": Vendor.GOOGLE,
    "samsung": Vendor.SAMSUNG,
    "oneplus": Vendor.ONEPLUS,
    "sony": Vendor.SONY,
    "asus": Vendor.ASUS,
    "nothing": Vendor.NOTHING,
}

_SOC_PATTERNS: list[tuple[SocVendor, tuple[str, ...]]] = [
    (SocVendor.TENSOR, ("tensor", "gs101", "gs201", "zuma")),
    (SocVendor.EXYNOS, ("exynos", "s5e", "universal")),
    (SocVendor.UNISOC, ("unisoc", "sprd", "ums", "spreadtrum")),
    (SocVendor.MEDIATEK, ("mediatek", "mt6", "mt8")),
    (
        SocVendor.QUALCOMM,
        (
            "qualcomm",
            "qcom",
            "qti",
            "msm",
            "sdm",
            "sm6",
            "sm7",
            "sm8",
            "lahaina",
            "kalama",
            "lito",
            "taro",
            "kona",
            "msmnile",
            "atoll",
            "holi",
        ),
    ),
]


def _vendor(manufacturer: str, brand: str) -> Vendor:
    m = manufacturer.lower()
    for key, v in _VENDOR_BY_MANUFACTURER.items():
        if key in m:
            return v
    b = brand.lower()
    for key, v in _VENDOR_BY_BRAND.items():
        if key in b:
            return v
    return Vendor.GENERIC


def _soc(*hints: str) -> SocVendor:
    text = " ".join(h.lower() for h in hints if h)
    for soc, patterns in _SOC_PATTERNS:
        if any(p in text for p in patterns):
            return soc
    return SocVendor.UNKNOWN


def _yes(v: str) -> bool:
    return v.strip().lower() in {"yes", "true", "1"}


def _lock(props: Mapping[str, str], fb: Mapping[str, str]) -> LockState:
    unlocked = fb.get("unlocked", "").strip().lower()
    if unlocked in {"yes", "no"}:
        return LockState.UNLOCKED if unlocked == "yes" else LockState.LOCKED
    vbs = props.get("ro.boot.verifiedbootstate", "").strip().lower()
    if vbs == "orange":
        return LockState.UNLOCKED
    if vbs in {"green", "yellow"}:
        return LockState.LOCKED
    fl = props.get("ro.boot.flash.locked", "").strip()
    if fl in {"0", "1"}:
        return LockState.LOCKED if fl == "1" else LockState.UNLOCKED
    ds = props.get("ro.boot.vbmeta.device_state", "").strip().lower()
    if ds in {"locked", "unlocked"}:
        return LockState.UNLOCKED if ds == "unlocked" else LockState.LOCKED
    return LockState.UNKNOWN


def _root_present(which: Mapping[str, bool]) -> str:
    for name in ("magisk", "ksud", "apd", "su"):
        if which.get(name):
            return {"ksud": "kernelsu", "apd": "apatch"}.get(name, name)
    return ""


def detect(raw: RawInfo) -> Device:
    p = raw.props
    fb = raw.fastboot_vars
    byname = raw.byname

    manufacturer = p.get("ro.product.manufacturer")
    brand = p.get("ro.product.brand")
    vendor = _vendor(manufacturer, brand)

    soc = _soc(
        p.get("ro.soc.manufacturer"),
        p.get("ro.soc.model"),
        p.get("ro.hardware"),
        p.get("ro.board.platform"),
        p.get("ro.hardware.chipname"),
        p.get("ro.boot.hardware.platform"),
    )
    if (
        vendor is Vendor.GOOGLE
        and soc is SocVendor.UNKNOWN
        and "tensor" in p.get("ro.soc.model", "").lower()
    ):
        soc = SocVendor.TENSOR

    slot_suffix = p.get("ro.boot.slot_suffix").strip() or fb.get("current-slot", "").strip()
    slot = slot_suffix.lstrip("_")
    slot_count = 0
    try:
        slot_count = int(fb.get("slot-count", "0"))
    except ValueError:
        slot_count = 0
    ab = bool(slot) or _yes(p.get("ro.build.ab_update")) or slot_count > 1

    first_api = p.get_int("ro.product.first_api_level", 0) or 0
    sdk = p.get_int("ro.build.version.sdk", 0) or 0

    has_init_boot = (
        "init_boot" in byname
        or "init_boot_a" in byname
        or _yes(fb.get("has-slot:init_boot", ""))
        or "partition-type:init_boot" in fb
        or first_api >= 33
    )
    has_vendor_boot = (
        "vendor_boot" in byname
        or "vendor_boot_a" in byname
        or _yes(fb.get("has-slot:vendor_boot", ""))
        or "partition-type:vendor_boot" in fb
    )
    patch_target = PatchTarget.INIT_BOOT if has_init_boot else PatchTarget.BOOT

    oem_raw = p.get("sys.oem_unlock_allowed").strip()
    oem_allowed: bool | None = None if oem_raw not in {"0", "1"} else oem_raw == "1"

    enc_state = p.get("ro.crypto.state")
    enc_type = p.get("ro.crypto.type")
    encryption = f"{enc_state}/{enc_type}" if enc_type else enc_state

    return Device(
        serial=p.get("ro.serialno") or fb.get("serialno", ""),
        model=p.get("ro.product.model"),
        brand=brand,
        manufacturer=manufacturer,
        codename=p.first("ro.product.device", "ro.build.product", "ro.product.name"),
        android=p.get("ro.build.version.release"),
        sdk=sdk,
        first_api_level=first_api,
        build_id=p.get("ro.build.id"),
        fingerprint=p.get("ro.build.fingerprint"),
        security_patch=p.get("ro.build.version.security_patch"),
        vendor=vendor,
        soc=soc,
        soc_model=p.first(
            "ro.soc.model", "ro.hardware.chipname", "ro.board.platform", "ro.hardware"
        ),
        ab=ab,
        slot=slot,
        has_init_boot=has_init_boot,
        has_vendor_boot=has_vendor_boot,
        dynamic_partitions=_yes(p.get("ro.boot.dynamic_partitions")),
        patch_target=patch_target,
        lock=_lock(p, fb),
        oem_unlock_allowed=oem_allowed,
        encryption=encryption,
        root_present=_root_present(raw.which),
        battery=raw.battery,
        warranty_bit=p.get("ro.boot.warranty_bit").strip(),
        kg_locked=p.get("ro.boot.other.locked").strip() == "1",
    )
