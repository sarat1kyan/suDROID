from sudroid.device.props import Props
from tests.conftest import getprop_text


def test_parse_basic() -> None:
    p = Props.parse("[ro.a]: [1]\n[ro.b]: []\n")
    assert p["ro.a"] == "1"
    assert p["ro.b"] == ""
    assert len(p) == 2


def test_parse_crlf_and_garbage_lines() -> None:
    p = Props.parse("[ro.a]: [x]\r\nnot a prop\r\n[ro.b]: [y]\r\n")
    assert p.get("ro.a") == "x"
    assert p.get("ro.b") == "y"


def test_parse_value_with_brackets() -> None:
    p = Props.parse("[ro.weird]: [a]: [b]\n")
    assert p["ro.weird"] == "a]: [b"


def test_get_int() -> None:
    p = Props.parse("[ro.sdk]: [34]\n[ro.bad]: [abc]\n")
    assert p.get_int("ro.sdk") == 34
    assert p.get_int("ro.bad") is None
    assert p.get_int("ro.missing", 7) == 7


def test_first() -> None:
    p = Props.parse("[a]: []\n[b]: [two]\n[c]: [three]\n")
    assert p.first("a", "b", "c") == "two"
    assert p.first("a", "zzz") == ""


def test_fixture_loads() -> None:
    p = Props.parse(getprop_text("pixel7"))
    assert p["ro.product.model"] == "Pixel 7"
    assert p.get_int("ro.build.version.sdk") == 34
