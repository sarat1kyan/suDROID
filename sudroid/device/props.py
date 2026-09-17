"""Parser for `getprop` output."""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping

_LINE = re.compile(r"^\[(?P<key>[^\]]+)\]: \[(?P<value>.*)\]$")


class Props(Mapping[str, str]):
    def __init__(self, data: Mapping[str, str] | None = None) -> None:
        self._data: dict[str, str] = dict(data or {})

    @classmethod
    def parse(cls, text: str) -> Props:
        data: dict[str, str] = {}
        for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
            line = raw.strip()
            m = _LINE.match(line)
            if m:
                data[m.group("key")] = m.group("value")
        return cls(data)

    def __getitem__(self, key: str) -> str:
        return self._data[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def get(self, key: str, default: str = "") -> str:  # type: ignore[override]
        return self._data.get(key, default)

    def get_int(self, key: str, default: int | None = None) -> int | None:
        raw = self._data.get(key, "")
        try:
            return int(raw)
        except ValueError:
            return default

    def first(self, *keys: str) -> str:
        for k in keys:
            v = self._data.get(k, "")
            if v:
                return v
        return ""

    def __repr__(self) -> str:
        return f"Props({len(self._data)} keys)"
