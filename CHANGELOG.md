# Changelog

## Unreleased

### Added
- Python package `sudroid` replacing the v2 shell scripts.
- `sudroid doctor`: host tool check, auto download of platform-tools.
- `sudroid info`: device detection (vendor, SoC, A/B slot, init_boot, lock state, root).
- `sudroid profiles`: vendor support matrix.
- Vendor profiles: Google, Samsung, Xiaomi, OnePlus, Motorola, Sony, ASUS, Nothing, generic.
- `--dry-run` blocks every device write.
- TOML config with `SUDROID_*` env overrides.

### Changed
- v2 scripts moved to `legacy/`, deprecated.

## 2.1 - 2024-10-31
- Bash script with menu-driven steps (superseded).

## 2.0
- Bash and PowerShell scripts for flashing app-patched boot images.
