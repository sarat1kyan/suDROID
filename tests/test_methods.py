import gzip
import json
from pathlib import Path

import httpx

from sudroid.root import apatch, kernelsu
from sudroid.root.github import Release, download_asset, latest_release

KSU_ASSETS = {
    "android12-5.10.209_2024-05-boot.img.gz": "https://x/a12-510.img.gz",
    "android12-5.10.209_2024-05-boot-lz4.img.gz": "https://x/a12-510-lz4.img.gz",
    "android13-5.15.148_2024-05-boot.img.gz": "https://x/a13-515.img.gz",
    "android14-6.1.75_2024-05-boot.img.gz": "https://x/a14-61.img.gz",
    "KernelSU_v0.9.5_11928-release.apk": "https://x/ksu.apk",
    "KernelSU_v0.9.5_11928-debug.apk": "https://x/ksu-debug.apk",
}


def test_kmi_parse() -> None:
    assert kernelsu.kmi_of("5.10.209-android12-9-00001-gabcdef") == "android12-5.10"
    assert kernelsu.kmi_of("6.1.75-android14-11-g123") == "android14-6.1"
    assert kernelsu.kmi_of("4.14.190-perf+") is None
    assert kernelsu.kmi_of("") is None


def test_match_boot_asset_and_manager() -> None:
    rel = Release(kernelsu.REPO, "v0.9.5", KSU_ASSETS)
    m = kernelsu.match_boot_asset(rel, "android12-5.10")
    assert m == ("android12-5.10.209_2024-05-boot.img.gz", "https://x/a12-510.img.gz")
    assert kernelsu.match_boot_asset(rel, "android11-5.4") is None
    assert kernelsu.manager_apk(rel) == "https://x/ksu.apk"


def test_apatch_manager() -> None:
    rel = Release(
        apatch.REPO,
        "10927",
        {
            "APatch_10927_10927-release.apk": "https://x/ap.apk",
            "APatch_10927-debug.apk": "https://x/apd.apk",
        },
    )
    assert apatch.manager_apk(rel) == "https://x/ap.apk"
    assert len(apatch.steps()) >= 4


def test_latest_release_with_etag_cache(tmp_path: Path) -> None:
    payload = {
        "tag_name": "v1",
        "assets": [{"name": "a.apk", "browser_download_url": "https://x/a.apk"}],
    }
    state = {"n": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        state["n"] += 1
        if req.headers.get("If-None-Match") == "W/abc":
            return httpx.Response(304)
        return httpx.Response(200, json=payload, headers={"ETag": "W/abc"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    r1 = latest_release(client, "o/r", tmp_path)
    r2 = latest_release(client, "o/r", tmp_path)
    assert r1 == r2 and r1.tag == "v1" and r1.assets["a.apk"].endswith("a.apk")
    assert state["n"] == 2
    cached = json.loads((tmp_path / "o_r.json").read_text())
    assert cached["etag"] == "W/abc"


def test_download_asset_and_gunzip(tmp_path: Path) -> None:
    body = gzip.compress(b"ANDROID!" + b"\x00" * 50)
    client = httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, content=body))
    )
    gz = download_asset(client, "https://x/boot.img.gz", tmp_path / "boot.img.gz")
    out = kernelsu.gunzip(gz, tmp_path / "boot.img")
    assert out.read_bytes().startswith(b"ANDROID!")
