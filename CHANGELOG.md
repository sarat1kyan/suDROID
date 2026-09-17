# Changelog

## 3.0.0 - 2026-09-17

Complete rewrite as a Python CLI. The v2 shell scripts are deprecated and kept under `legacy/`.

### Added
- `sudroid info`: device report from getprop and fastboot vars: vendor, SoC, kernel, A/B slot, init_boot, dynamic partitions, lock state, OEM unlock toggle, encryption, root presence, battery.
- `sudroid doctor`: host tool check with automatic platform-tools download, udev and driver hints.
- `sudroid root`: acquire stock image, back up, patch on device with Magisk's own boot_patch.sh, test boot via `fastboot boot`, flash to the current slot, install the manager, verify.
- `--firmware`: OTA zip (payload.bin), raw payload.bin, Pixel factory zip, Samsung AP tar (.tar.md5, lz4).
- `--auto-fetch`: download the Pixel factory image for the installed build with sha256 verification.
- `--method kernelsu`: match the device KMI to a KernelSU GKI prebuilt, test boot, flash, install manager.
- `--method apatch`: install the manager, stage the stock image, hand off to `sudroid flash`.
- Samsung: patched init_boot/boot and vbmeta flashed with Heimdall after `adb reboot download`, or `--odin` to write an Odin AP tar with md5 trailer.
- `sudroid unlock`: vendor specific guidance and automation (Google, OnePlus, Nothing, generic fastboot, Motorola unlock data flow, Sony code flow). Typed UNLOCK confirmation. Requires a stock backup unless `--i-know`.
- `sudroid backup`, `sudroid restore`, `sudroid flash`, `sudroid patch`, `sudroid verify`, `sudroid profiles`, `sudroid config`.
- Workflow engine with checkpointed sessions, `--resume`, undo of completed writes on failure, `--dry-run` that blocks every device write.
- Vendor profiles: Google, Samsung, Xiaomi, OnePlus, Motorola, Sony, ASUS, Nothing, generic (MediaTek and Unisoc hints).
- TOML config with `SUDROID_*` environment overrides, rotating file log, `--json` output.
- CI on Linux, macOS and Windows for Python 3.10 to 3.13. Release workflow builds wheels and single file binaries.

### Changed
- Partition listing from the device is authoritative for init_boot detection; the launch API heuristic is only a fallback and is re-checked with fastboot before flashing.
- No more `sudo` package installs. `doctor` prints what to install.

### Removed
- Automatic `fastboot oem unlock` without confirmation.
- `adb backup` as a safety step.

## 2.1 - 2024-10-31
- Menu driven bash script (superseded).

## 2.0
- Bash and PowerShell scripts for flashing app-patched boot images.
