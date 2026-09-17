import hashlib
from pathlib import Path

import httpx
import pytest

from sudroid.errors import PreconditionError
from sudroid.images.pixel_factory import FactoryImage, download, find_image, list_builds

HTML = """
<tr id="panther"><td>14.0.0 (UP1A.231005.007, Oct 2023)</td>
<td><a href="https://dl.google.com/dl/android/aosp/panther-up1a.231005.007-factory-11aa22bb.zip">Link</a></td>
<td>aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa</td></tr>
<tr><td>14.0.0 (UP1A.231105.003, Nov 2023)</td>
<td><a href="https://dl.google.com/dl/android/aosp/panther-up1a.231105.003-factory-33cc44dd.zip">Link</a></td>
<td>bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb</td></tr>
<tr><td>14.0.0 (UP1A.231105.003, Nov 2023)</td>
<td><a href="https://dl.google.com/dl/android/aosp/cheetah-up1a.231105.003-factory-55ee66ff.zip">Link</a></td>
<td>cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc</td></tr>
"""


def test_find_and_list() -> None:
    img = find_image(HTML, "panther", "UP1A.231105.003")
    assert img is not None
    assert img.url.endswith("panther-up1a.231105.003-factory-33cc44dd.zip")
    assert img.sha256 == "b" * 64
    assert img.filename == "panther-up1a.231105.003-factory-33cc44dd.zip"
    assert find_image(HTML, "panther", "ZZZ") is None
    assert find_image(HTML, "cheetah", "UP1A.231005.007") is None
    assert list_builds(HTML, "panther") == ["UP1A.231005.007", "UP1A.231105.003"]


def test_download_verifies_sha(tmp_path: Path) -> None:
    body = b"PK" + b"\x00" * 100
    good = FactoryImage(
        "panther",
        "X",
        "https://dl.google.com/dl/android/aosp/p-x-factory-00000000.zip",
        hashlib.sha256(body).hexdigest(),
    )
    calls = {"n": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, content=body)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    p = download(client, good, tmp_path)
    assert p.is_file() and calls["n"] == 1
    download(client, good, tmp_path)
    assert calls["n"] == 1  # cached
    bad = FactoryImage(
        "panther", "X", "https://dl.google.com/dl/android/aosp/p-y-factory-00000000.zip", "0" * 64
    )
    with pytest.raises(PreconditionError):
        download(client, bad, tmp_path)
    assert not (tmp_path / "p-y-factory-00000000.zip").exists()
