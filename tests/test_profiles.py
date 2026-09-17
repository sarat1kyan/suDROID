import re

from sudroid.device.detect import detect
from sudroid.device.model import FlashBackend, PatchTarget, RawInfo, Vendor
from sudroid.device.profiles import all_profiles, profile_for
from sudroid.device.props import Props
from tests.conftest import getprop_text


def dev(name: str) -> object:
    return detect(RawInfo(props=Props.parse(getprop_text(name))))


def test_registry_maps_fixtures() -> None:
    expected = {
        "pixel7": Vendor.GOOGLE,
        "pixel5": Vendor.GOOGLE,
        "oneplus9": Vendor.ONEPLUS,
        "s23": Vendor.SAMSUNG,
        "mi11": Vendor.XIAOMI,
        "motog": Vendor.MOTOROLA,
        "xperia5": Vendor.SONY,
        "generic_mtk": Vendor.GENERIC,
    }
    for name, vendor in expected.items():
        d = detect(RawInfo(props=Props.parse(getprop_text(name))))
        assert profile_for(d).vendor is vendor, name


def test_all_profiles_unique_vendors() -> None:
    vendors = [p.vendor for p in all_profiles()]
    assert len(vendors) == len(set(vendors)) == 9


def test_samsung_not_automatable_uses_heimdall() -> None:
    d = detect(RawInfo(props=Props.parse(getprop_text("s23"))))
    p = profile_for(d)
    assert p.flash_backend is FlashBackend.HEIMDALL
    assert p.unlock_commands(d) == []
    assert p.supports_test_boot is False
    assert p.flash_partition(d, PatchTarget.INIT_BOOT) == "INIT_BOOT"
    codes = {q.code for q in p.quirks(d)}
    assert {"no-fastboot", "knox", "kg"} <= codes


def test_motorola_needs_unlock_data() -> None:
    d = detect(RawInfo(props=Props.parse(getprop_text("motog"))))
    p = profile_for(d)
    assert p.needs_unlock_data(d)
    assert p.unlock_data_command(d) == ["oem", "get_unlock_data"]
    assert p.unlock_command_with_key(d, "ABC") == ["oem", "unlock", "ABC"]
    assert p.unlock_commands(d) == []


def test_sony_key_prefixed() -> None:
    d = detect(RawInfo(props=Props.parse(getprop_text("xperia5"))))
    p = profile_for(d)
    assert p.unlock_command_with_key(d, "DEADBEEF") == ["oem", "unlock", "0xDEADBEEF"]
    assert p.unlock_command_with_key(d, "0xdeadbeef") == ["oem", "unlock", "0xdeadbeef"]
    assert any(q.code == "drm-keys" for q in p.quirks(d))


def test_google_targets() -> None:
    p7 = detect(RawInfo(props=Props.parse(getprop_text("pixel7"))))
    p5 = detect(RawInfo(props=Props.parse(getprop_text("pixel5"))))
    prof = profile_for(p7)
    assert prof.patch_target(p7) is PatchTarget.INIT_BOOT
    assert prof.patch_target(p5) is PatchTarget.BOOT
    assert prof.flash_partition(p7, PatchTarget.INIT_BOOT) == "init_boot_a"
    assert prof.flash_partition(p5, PatchTarget.BOOT) == "boot_b"
    assert prof.unlock_commands(p7) == [["flashing", "unlock"]]


def test_generic_mtk_quirk() -> None:
    d = detect(RawInfo(props=Props.parse(getprop_text("generic_mtk"))))
    p = profile_for(d)
    assert any(q.code == "mtk" for q in p.quirks(d))
    assert p.unlock_commands(d) == [["flashing", "unlock"], ["oem", "unlock"]]


def test_xiaomi_not_automatable() -> None:
    d = detect(RawInfo(props=Props.parse(getprop_text("mi11"))))
    p = profile_for(d)
    assert p.unlock_automatable is False
    assert p.unlock_commands(d) == []


def test_no_short_links_or_plain_http() -> None:
    url = re.compile(r"https?://[^\s)\"']+")
    banned = ("adshnk", "bit.ly", "t.co/", "goo.gl", "tinyurl")
    for p in all_profiles():
        for name in ("pixel7", "s23", "mi11", "motog", "xperia5", "generic_mtk"):
            d = detect(RawInfo(props=Props.parse(getprop_text(name))))
            text = " ".join(p.unlock_steps(d) + [q.message for q in p.quirks(d)] + [p.unlock_url])
            for u in url.findall(text):
                assert u.startswith("https://"), u
                assert not any(b in u for b in banned), u
