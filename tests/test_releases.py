import io
import json
import zipfile
from pathlib import Path

import httpx
import pytest

from sudroid.errors import PatchError
from sudroid.root.releases import download_apk, fetch_release, validate_apk


def fake_apk(
    abis: tuple[str, ...] = ("arm64-v8a", "armeabi-v7a"), extra: dict[str, bytes] | None = None
) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("assets/boot_patch.sh", "#!/system/bin/sh\necho patch\n")
        zf.writestr("assets/util_functions.sh", 'ui_print() { echo "$1"; }\n')
        zf.writestr("assets/stub.apk", b"PK-stub")
        for abi in abis:
            for lib in ("magiskboot", "magiskinit", "magisk", "init-ld"):
                zf.writestr(f"lib/{abi}/lib{lib}.so", f"{abi}-{lib}".encode())
        for k, v in (extra or {}).items():
            zf.writestr(k, v)
    return buf.getvalue()


def test_fetch_release_stable() -> None:
    payload = {
        "magisk": {"version": "28.1", "versionCode": "28100", "link": "https://x/Magisk-v28.1.apk"}
    }

    def handler(req: httpx.Request) -> httpx.Response:
        assert "stable.json" in str(req.url)
        return httpx.Response(200, content=json.dumps(payload).encode())

    rel = fetch_release(httpx.Client(transport=httpx.MockTransport(handler)))
    assert rel.version == "28.1" and rel.version_code == 28100
    assert rel.tag == "v28.1"
    assert rel.filename == "Magisk-v28.1-28100.apk"


def test_fetch_release_pinned_no_network() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        raise AssertionError("no network expected")

    rel = fetch_release(httpx.Client(transport=httpx.MockTransport(handler)), pinned="27.0")
    assert rel.tag == "v27.0"
    assert rel.apk_url.endswith("/v27.0/Magisk-v27.0.apk")


def test_fetch_release_bad_channel_and_pin() -> None:
    c = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, content=b"{}")))
    with pytest.raises(PatchError):
        fetch_release(c, channel="nightly")
    with pytest.raises(PatchError):
        fetch_release(c, pinned="../evil")
    with pytest.raises(PatchError):
        fetch_release(c)  # malformed


def test_download_apk_caches_and_validates(tmp_path: Path) -> None:
    apk = fake_apk()
    calls = {"n": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, content=apk)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    rel = fetch_release(client, pinned="v28.0")
    p1 = download_apk(client, rel, tmp_path)
    p2 = download_apk(client, rel, tmp_path)
    assert p1 == p2 and p1.is_file()
    assert calls["n"] == 1
    assert p1.with_suffix(".apk.sha256").is_file()
    # corrupt cache -> re-download
    p1.write_bytes(b"junk")
    download_apk(client, rel, tmp_path)
    assert calls["n"] == 2


def test_validate_apk_rejects_non_magisk(tmp_path: Path) -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("classes.dex", b"x")
    p = tmp_path / "a.apk"
    p.write_bytes(buf.getvalue())
    with pytest.raises(PatchError):
        validate_apk(p)
    p.write_bytes(b"not a zip")
    with pytest.raises(PatchError):
        validate_apk(p)
