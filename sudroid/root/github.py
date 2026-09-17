"""GitHub release lookup with ETag cache."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import httpx

from sudroid.errors import PreconditionError

log = logging.getLogger(__name__)

API = "https://api.github.com/repos/{repo}/releases/latest"


@dataclass(frozen=True)
class Release:
    repo: str
    tag: str
    assets: dict[str, str]  # name -> browser_download_url

    def find(self, *needles: str, exclude: tuple[str, ...] = ()) -> str | None:
        for name, url in self.assets.items():
            low = name.lower()
            if all(n.lower() in low for n in needles) and not any(
                e.lower() in low for e in exclude
            ):
                return url
        return None


def latest_release(client: httpx.Client, repo: str, cache: Path | None = None) -> Release:
    url = API.format(repo=repo)
    headers = {"Accept": "application/vnd.github+json"}
    cached: dict[str, object] | None = None
    cache_file = (cache / f"{repo.replace('/', '_')}.json") if cache else None
    if cache_file and cache_file.is_file():
        try:
            cached = json.loads(cache_file.read_text())
            etag = cached.get("etag") if cached else None
            if isinstance(etag, str):
                headers["If-None-Match"] = etag
        except json.JSONDecodeError:
            cached = None
    r = client.get(url, headers=headers, follow_redirects=True, timeout=30)
    if r.status_code == 304 and cached:
        data = cached.get("data")
    else:
        if r.status_code == 403 and cached:
            log.warning("GitHub API rate limited, using cached release data for %s", repo)
            data = cached.get("data")
        else:
            r.raise_for_status()
            data = r.json()
            if cache_file:
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                cache_file.write_text(json.dumps({"etag": r.headers.get("ETag", ""), "data": data}))
    if not isinstance(data, dict):
        raise PreconditionError(f"unexpected release data for {repo}")
    tag = str(data.get("tag_name", ""))
    assets = {
        str(a.get("name")): str(a.get("browser_download_url"))
        for a in data.get("assets", [])
        if isinstance(a, dict) and a.get("name") and a.get("browser_download_url")
    }
    if not tag:
        raise PreconditionError(f"no release tag for {repo}")
    return Release(repo, tag, assets)


def download_asset(client: httpx.Client, url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file():
        return dest
    tmp = dest.with_suffix(dest.suffix + ".part")
    with client.stream("GET", url, follow_redirects=True, timeout=600) as r:
        r.raise_for_status()
        with tmp.open("wb") as fh:
            for chunk in r.iter_bytes(1 << 20):
                fh.write(chunk)
    tmp.replace(dest)
    return dest
