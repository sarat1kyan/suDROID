import pytest

from sudroid.device.detect import detect
from sudroid.device.model import LockState, PatchTarget, RawInfo, SocVendor, Vendor
from sudroid.device.props import Props
from tests.conftest import getprop_text


def raw(name: str, **kw: object) -> RawInfo:
    return RawInfo(props=Props.parse(getprop_text(name)), **kw)  # type: ignore[arg-type]


def test_pixel7() -> None:
    d = detect(raw("pixel7"))
    assert d.vendor is Vendor.GOOGLE
    assert d.soc is SocVendor.TENSOR
    assert d.ab and d.slot == "a"
    assert d.has_init_boot
    assert d.patch_target is PatchTarget.INIT_BOOT
    assert d.lock is LockState.UNLOCKED
    assert d.oem_unlock_allowed is True
    assert d.codename == "panther"
    assert d.slot_suffix == "_a"


def test_pixel5_boot_target_locked() -> None:
    d = detect(raw("pixel5"))
    assert d.vendor is Vendor.GOOGLE
    assert d.soc is SocVendor.QUALCOMM
    assert d.patch_target is PatchTarget.BOOT
    assert d.lock is LockState.LOCKED
    assert d.slot == "b"


def test_oneplus9() -> None:
    d = detect(raw("oneplus9"))
    assert d.vendor is Vendor.ONEPLUS
    assert d.soc is SocVendor.QUALCOMM
    assert d.patch_target is PatchTarget.BOOT
    assert d.is_unlocked


def test_s23() -> None:
    d = detect(raw("s23"))
    assert d.vendor is Vendor.SAMSUNG
    assert d.soc is SocVendor.QUALCOMM
    assert d.slot == ""
    assert d.ab  # ab_update true without slot suffix prop
    assert d.patch_target is PatchTarget.INIT_BOOT
    assert d.lock is LockState.LOCKED


def test_mi11() -> None:
    d = detect(raw("mi11"))
    assert d.vendor is Vendor.XIAOMI
    assert d.lock is LockState.LOCKED
    assert d.oem_unlock_allowed is False


def test_motog() -> None:
    d = detect(raw("motog"))
    assert d.vendor is Vendor.MOTOROLA
    assert d.soc is SocVendor.QUALCOMM
    assert d.patch_target is PatchTarget.BOOT
    assert d.dynamic_partitions is False


def test_xperia5() -> None:
    d = detect(raw("xperia5"))
    assert d.vendor is Vendor.SONY
    assert d.soc is SocVendor.QUALCOMM


def test_generic_mtk() -> None:
    d = detect(raw("generic_mtk"))
    assert d.vendor is Vendor.GENERIC
    assert d.soc is SocVendor.MEDIATEK
    assert not d.ab
    assert d.slot_suffix == ""


def test_brand_fallback_redmi() -> None:
    p = Props.parse("[ro.product.manufacturer]: [Unknown]\n[ro.product.brand]: [Redmi]\n")
    assert detect(RawInfo(props=p)).vendor is Vendor.XIAOMI


def test_fastboot_unlocked_wins_over_props() -> None:
    d = detect(raw("pixel5", fastboot_vars={"unlocked": "yes"}))
    assert d.lock is LockState.UNLOCKED


def test_byname_init_boot_forces_target() -> None:
    d = detect(raw("pixel5", byname=frozenset({"boot_a", "boot_b", "init_boot_a", "init_boot_b"})))
    assert d.patch_target is PatchTarget.INIT_BOOT


def test_lock_unknown_when_no_signals() -> None:
    p = Props.parse("[ro.product.manufacturer]: [x]\n")
    assert detect(RawInfo(props=p)).lock is LockState.UNKNOWN


@pytest.mark.parametrize(
    "which,expected",
    [
        ({"su": True}, "su"),
        ({"su": True, "magisk": True}, "magisk"),
        ({"ksud": True}, "kernelsu"),
        ({"apd": True}, "apatch"),
        ({}, ""),
    ],
)
def test_root_present(which: dict[str, bool], expected: str) -> None:
    d = detect(raw("pixel7", which=which))
    assert d.root_present == expected


def test_battery_passthrough() -> None:
    assert detect(raw("pixel7", battery=77)).battery == 77
