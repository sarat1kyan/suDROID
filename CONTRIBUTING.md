# Contributing

## Setup

    uv venv -p 3.12 .venv
    uv pip install -p .venv/bin/python -e '.[dev]'

## Checks

    ruff check . && ruff format --check .
    mypy
    pytest

All three must pass. CI runs them on Linux, macOS and Windows for Python 3.10 to 3.13.

## Rules

- Only `sudroid/tools/` may spawn processes.
- Every device write passes `mutating=True` to the runner.
- Vendor specific logic lives in `sudroid/device/profiles/`.
- Add a getprop fixture under `tests/fixtures/getprop/` when adding a device family.
- No shortened links. No `sudo` in code.

## Device fixtures

Dump with `adb shell getprop > tests/fixtures/getprop/<codename>.txt`, strip
serial numbers and personal data, keep the keys listed in `docs/specs`.
