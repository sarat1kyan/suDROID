"""Rich tables and panels."""

from __future__ import annotations

from rich.table import Table

from sudroid.device.model import Device, LockState
from sudroid.device.profiles.base import Quirk, VendorProfile


def device_table(d: Device, profile: VendorProfile) -> Table:
    t = Table(title="Device", show_header=False, box=None, pad_edge=False)
    t.add_column("k", style="bold")
    t.add_column("v")
    lock_style = {"unlocked": "green", "locked": "red", "unknown": "yellow"}[d.lock.value]
    rows = [
        ("Model", f"{d.brand} {d.model}"),
        ("Codename", d.codename),
        ("Serial", d.serial),
        ("Vendor profile", profile.name),
        ("Android", f"{d.android} (SDK {d.sdk}, first API {d.first_api_level})"),
        ("Build", d.build_id),
        ("Security patch", d.security_patch),
        ("SoC", f"{d.soc.value} {d.soc_model}".strip()),
        ("A/B", f"yes, slot {d.slot or '?'}" if d.ab else "no"),
        ("Patch target", profile.patch_target(d).value),
        ("init_boot", "yes" if d.has_init_boot else "no"),
        ("vendor_boot", "yes" if d.has_vendor_boot else "no"),
        ("Dynamic partitions", "yes" if d.dynamic_partitions else "no"),
        ("Bootloader", f"[{lock_style}]{d.lock.value}[/{lock_style}]"),
        (
            "OEM unlock allowed",
            "unknown"
            if d.oem_unlock_allowed is None
            else ("yes" if d.oem_unlock_allowed else "no"),
        ),
        ("Encryption", d.encryption or "unknown"),
        ("Root present", d.root_present or "none"),
        ("Battery", f"{d.battery}%" if d.battery is not None else "unknown"),
        ("Flash backend", profile.flash_backend.value),
        ("Test boot", "yes" if profile.supports_test_boot else "no"),
    ]
    if d.vendor.value == "samsung":
        rows.append(("Knox warranty bit", d.warranty_bit or "unknown"))
    for k, v in rows:
        t.add_row(k, v)
    return t


def quirks_table(quirks: list[Quirk]) -> Table:
    t = Table(title="Notes", show_header=False, box=None, pad_edge=False)
    t.add_column("s")
    t.add_column("m")
    style = {"info": "cyan", "warn": "yellow", "block": "red"}
    for q in quirks:
        t.add_row(f"[{style.get(q.severity, 'cyan')}]{q.severity}[/]", q.message)
    return t


def support_matrix(profiles: list[VendorProfile]) -> Table:
    t = Table(title="Vendor support")
    t.add_column("Vendor")
    t.add_column("Unlock")
    t.add_column("Flash")
    t.add_column("Test boot")
    t.add_column("Wipes on unlock")
    for p in profiles:
        t.add_row(
            p.name,
            "automated" if p.unlock_automatable else "guided",
            p.flash_backend.value,
            "yes" if p.supports_test_boot else "no",
            "yes" if p.unlock_wipes_data else "no",
        )
    return t


def doctor_table(rows: list[tuple[str, str, str]]) -> Table:
    t = Table(title="Host check")
    t.add_column("Check")
    t.add_column("Status")
    t.add_column("Detail")
    style = {"ok": "green", "warn": "yellow", "fail": "red"}
    for name, status, detail in rows:
        t.add_row(name, f"[{style.get(status, 'white')}]{status}[/]", detail)
    return t


def lock_hint(d: Device) -> str:
    if d.lock is LockState.LOCKED:
        return "Bootloader locked. Run `sudroid unlock` first."
    if d.lock is LockState.UNKNOWN:
        return "Lock state unknown. Reboot to bootloader and run `sudroid info` again."
    return ""
