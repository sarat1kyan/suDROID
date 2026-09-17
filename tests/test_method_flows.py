import gzip
import json
from pathlib import Path

import httpx
import pytest
from typer.testing import CliRunner

from sudroid import cli
from sudroid.workflow import steps
from tests.flow_helpers import FakeDevice, boot_image, install

runner = CliRunner()

KSU_RELEASE = {
    "tag_name": "v0.9.5",
    "assets": [
        {
            "name": "android12-5.10.209_2024-05-boot.img.gz",
            "browser_download_url": "https://gh/ksu-boot.img.gz",
        },
        {
            "name": "android12-5.10.209_2024-05-boot-lz4.img.gz",
            "browser_download_url": "https://gh/lz4.gz",
        },
        {"name": "KernelSU_v0.9.5_11928-release.apk", "browser_download_url": "https://gh/ksu.apk"},
    ],
}
APATCH_RELEASE = {
    "tag_name": "10927",
    "assets": [
        {"name": "APatch_10927_10927-release.apk", "browser_download_url": "https://gh/apatch.apk"}
    ],
}


def gh_client(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        url = str(req.url)
        if "KernelSU/releases" in url:
            return httpx.Response(200, json=KSU_RELEASE)
        if "APatch/releases" in url:
            return httpx.Response(200, json=APATCH_RELEASE)
        if url.endswith("ksu-boot.img.gz"):
            return httpx.Response(200, content=gzip.compress(boot_image(kernel=900, ramdisk=10)))
        if url.endswith(".apk"):
            return httpx.Response(200, content=b"PK-apk")
        if url.endswith(".json"):
            return httpx.Response(
                200,
                content=json.dumps(
                    {
                        "magisk": {
                            "version": "28.0",
                            "versionCode": "28000",
                            "link": "https://x/m.apk",
                        }
                    }
                ).encode(),
            )
        return httpx.Response(404)

    monkeypatch.setattr(
        steps, "_http_client", lambda: httpx.Client(transport=httpx.MockTransport(handler))
    )


def test_kernelsu_gki_flow(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dev = FakeDevice(
        "pixel7",
        byname="boot_a boot_b init_boot_a init_boot_b",
        kernel="5.10.209-android12-9-00001-gabcdef",
    )
    install(monkeypatch, tmp_path, dev)
    gh_client(monkeypatch)
    stock = tmp_path / "init_boot.img"
    stock.write_bytes(boot_image(kernel=0, version=4))
    r = runner.invoke(cli.app, ["--yes", "root", "--method", "kernelsu", "--image", str(stock)])
    assert r.exit_code == 0, r.output
    # KernelSU prebuilt goes to boot, not init_boot, and is test booted first
    assert dev.booted and dev.booted[0].endswith("kernelsu_boot.img")
    assert [p for p, _ in dev.flashed] == ["boot_a"]
    assert any(
        c[3:5] == ("install", "-r") and c[5].endswith("KernelSU_v0.9.5_11928-release.apk")
        for c in dev.runner.mutating_calls
    )
    assert "root verified" in r.output


def test_kernelsu_non_gki_guides(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dev = FakeDevice("oneplus9", kernel="4.19.157-perf+")
    install(monkeypatch, tmp_path, dev)
    gh_client(monkeypatch)
    r = runner.invoke(cli.app, ["--yes", "root", "--method", "kernelsu", "--skip-backup"])
    assert r.exit_code == 20, r.output
    assert "not a GKI kernel" in r.output
    assert "sudroid flash" in r.output
    assert dev.flashed == []


def test_kernelsu_skip_backup_needs_no_stock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dev = FakeDevice("oneplus9", kernel="5.10.209-android12-9-g1")
    install(monkeypatch, tmp_path, dev)
    gh_client(monkeypatch)
    r = runner.invoke(cli.app, ["--yes", "root", "--method", "kernelsu", "--skip-backup"])
    assert r.exit_code == 0, r.output
    assert [p for p, _ in dev.flashed] == ["boot_a"]


def test_apatch_flow_installs_and_stages(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dev = FakeDevice("oneplus9")
    install(monkeypatch, tmp_path, dev)
    gh_client(monkeypatch)
    stock = tmp_path / "boot.img"
    stock.write_bytes(boot_image())
    r = runner.invoke(cli.app, ["--yes", "root", "--method", "apatch", "--image", str(stock)])
    assert r.exit_code == 0, r.output
    assert dev.flashed == [] and dev.booted == []
    pushes = [c for c in dev.runner.mutating_calls if c[3] == "push"]
    assert any(c[-1] == "/sdcard/Download/stock_boot.img" for c in pushes)
    assert any(c[3:5] == ("install", "-r") and "APatch" in c[5] for c in dev.runner.mutating_calls)
    assert "SuperKey" in r.output
