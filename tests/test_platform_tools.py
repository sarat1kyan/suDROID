import io
import os
import stat
import zipfile
from pathlib import Path

import httpx
import pytest

from sudroid.errors import ToolMissingError
from sudroid.tools import platform_tools as pt


def _zip_with(names: list[str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for n in names:
            info = zipfile.ZipInfo(n)
            info.external_attr = (0o755 << 16) if not n.endswith("/") else (0o40755 << 16)
            zf.writestr(info, b"#!/bin/sh\necho fake\n")
    return buf.getvalue()


def test_locate_override_file(tmp_path: Path) -> None:
    exe = tmp_path / "adb"
    exe.write_text("x")
    assert pt.locate("adb", override=str(exe)) == exe


def test_locate_override_missing(tmp_path: Path) -> None:
    assert pt.locate("adb", override=str(tmp_path / "nope")) is None


def test_locate_extra_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", str(tmp_path / "emptypath"))
    monkeypatch.setattr(pt, "common_dirs", lambda: [])
    d = tmp_path / "pt"
    d.mkdir()
    exe = d / pt._exe("fastboot")
    exe.write_text("x")
    assert pt.locate("fastboot", extra_dirs=[d]) == exe


def test_ensure_raises_when_no_download(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.setattr(pt, "common_dirs", lambda: [])
    with pytest.raises(ToolMissingError) as ei:
        pt.ensure("adb", auto_download=False)
    assert ei.value.exit_code == 12
    assert ei.value.hint


def test_download_and_ensure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.setattr(pt, "common_dirs", lambda: [])
    payload = _zip_with(["platform-tools/", "platform-tools/adb", "platform-tools/fastboot"])

    def handler(request: httpx.Request) -> httpx.Response:
        assert "platform-tools-latest" in str(request.url)
        return httpx.Response(200, content=payload)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    cache = tmp_path / "cache"
    path = pt.ensure("adb", client=client, cache=cache)
    assert path == cache / "platform-tools" / pt._exe("adb")
    assert path.is_file()
    if os.name == "posix":
        assert path.stat().st_mode & stat.S_IXUSR


def test_download_rejects_sibling_prefix(tmp_path: Path) -> None:
    (tmp_path / "c").mkdir()
    payload = _zip_with(["../c-evil/x"])
    client = httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, content=payload))
    )
    with pytest.raises(ToolMissingError):
        pt.download_platform_tools(client, tmp_path / "c", url="https://example.invalid/x.zip")


def test_download_rejects_path_traversal(tmp_path: Path) -> None:
    payload = _zip_with(["../evil"])
    client = httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, content=payload))
    )
    with pytest.raises(ToolMissingError):
        pt.download_platform_tools(client, tmp_path / "c", url="https://example.invalid/x.zip")


def test_host_os_known() -> None:
    assert pt.host_os() in {"linux", "darwin", "windows"}
