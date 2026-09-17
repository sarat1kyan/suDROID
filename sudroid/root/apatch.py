"""APatch: kernel patch based root. The manager app patches the boot image."""

from __future__ import annotations

from sudroid.root.github import Release

REPO = "bmax121/APatch"


def manager_apk(rel: Release) -> str | None:
    return rel.find(".apk", exclude=("debug",)) or rel.find(".apk")


def steps() -> list[str]:
    return [
        "Open the APatch app, tap the patch button, pick the stock boot.img this tool copied "
        "to the device Download folder",
        "Set a SuperKey (8 or more characters), remember it",
        "After patching, copy the apatch_patched_*.img back to this computer",
        "Run: sudroid flash <apatch_patched.img> --partition boot --test-boot",
        "Open APatch, enter the SuperKey, confirm root with `sudroid verify`",
    ]
