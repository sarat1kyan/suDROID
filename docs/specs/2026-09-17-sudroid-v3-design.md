# suDROID v3 design

Date: 2026-09-17
Status: approved

## 1. Problem

v2.0 and v2.1 are two divergent shell scripts (bash + PowerShell) with a
README that describes features that do not exist. v2.1 cannot work as
written: it runs Android ARM binaries on the host, pulls partitions that
need root, ignores A/B slots and init_boot, auto-unlocks the bootloader
without confirmation, and claims Samsung support without any Samsung
flashing path. There are no tests, no CI, no releases.

v3 replaces both scripts with one Python CLI that detects the device
properly, patches on the host with magiskboot, test-boots before writing,
and supports every major vendor path including Samsung (Heimdall/Odin).

## 2. Scope

In scope:

- Linux, macOS, Windows hosts. Python 3.10+.
- Root methods: Magisk (automated host-side patch), APatch and KernelSU
  (release lookup, guidance, flash of user-supplied patched image).
- Vendors: Google, Samsung, Xiaomi/Redmi/POCO, OnePlus, Motorola, Sony,
  ASUS, Nothing, generic fastboot. MediaTek and Unisoc chipset hints for
  unlock.
- Partition targets: boot, init_boot, vendor_boot (KSU awareness), vbmeta
  (Samsung flow).
- Stock image sources: user file, rooted dd pull, factory image zip,
  OTA payload.bin, Samsung AP tar (lz4), Pixel factory image auto-fetch.
- Backup and restore of stock images with manifest.
- Dry-run, resume, structured logs.
- PyPI package, PyInstaller binaries, GitHub Actions CI and release.

Out of scope for v3.0:

- GUI.
- Custom recovery (TWRP) installation.
- App data backup. `adb backup` is deprecated and unreliable; offered as
  optional with a warning, never as a safety guarantee.
- Flashing full firmware.

## 3. Architecture

Single package `sudroid`. Layers, top to bottom:

```
cli            Typer commands, argument parsing, exit codes
workflow       step engine: preconditions, run, undo, checkpoints, resume
root           magisk / apatch / kernelsu, unified patcher
images         stock image acquisition and verification
backup         manifest, save, restore
device         props, detection, vendor profiles
tools          subprocess wrappers: adb, fastboot, heimdall, magiskboot, lz4/tar, platform-tools fetch
ui             prompts, confirmations, tables
config, log    TOML config, Rich console, rotating file log, JSON mode
```

Rules:

- Only `tools/` spawns subprocesses. Everything above talks to typed
  clients. Tests replace `tools/` with fakes.
- `device/detect.py` produces one immutable `Device` dataclass. All
  decisions downstream read from it, never from raw props.
- Vendor profiles are data plus small strategy methods. No vendor
  branching outside `device/profiles/`.
- Every write to the device goes through `workflow/engine.py` so it is
  logged, confirmable, dry-runnable, and undoable.

### 3.1 Package layout

```
sudroid/
  __init__.py  __main__.py  cli.py  config.py  log.py  errors.py
  tools/
    base.py            run(), Result, timeout, dry-run recording
    adb.py             AdbClient
    fastboot.py        FastbootClient
    heimdall.py        HeimdallClient
    magiskboot.py      MagiskBoot (extract from APK, unpack, cpio, repack, verify)
    archive.py         zip, tar, lz4, payload.bin readers
    platform_tools.py  locate or download adb/fastboot/heimdall
  device/
    props.py           Props (dict wrapper, typed getters)
    detect.py          detect(adb, fastboot) -> Device
    model.py           Device, Vendor, Soc, LockState, PatchTarget, FlashBackend enums
    profiles/
      base.py          VendorProfile protocol
      google.py samsung.py xiaomi.py oneplus.py motorola.py sony.py asus.py nothing.py generic.py
      registry.py      profile_for(device)
  root/
    releases.py        GitHub release lookup with cache, fallback, sha256
    magisk.py          APK download, magiskboot extraction, boot_patch port
    apatch.py          release info, guidance
    kernelsu.py        release info, guidance
    patcher.py         patch(stock_image, method, device) -> PatchedImage
  images/
    sources.py         resolve stock image from user file / device / firmware archive
    pixel_factory.py   Pixel factory image lookup by build id
    verify.py          header parse, sha256, magiskboot verify
  backup/
    manager.py         BackupManifest, save(), list(), restore()
  workflow/
    engine.py          Step, Plan, run(plan), checkpoint file, resume
    steps.py           concrete steps for root / unlock / restore flows
  ui/
    prompts.py         confirm(), typed_confirm(word), select()
    render.py          device table, plan table, support matrix
tests/
  fakes/               FakeAdb, FakeFastboot, FakeHeimdall, FakeMagiskBoot
  fixtures/            getprop + getvar dumps per device (pixel7, pixel5, oneplus9, s23, mi11, motog, xperia5)
  test_*.py
```

## 4. Commands

```
sudroid doctor              host tools, versions, udev rules (Linux), driver hints (Windows), adb server state
sudroid info                device report, JSON with --json
sudroid backup [--from FILE|--from-device]
sudroid unlock [--i-know]   vendor-aware unlock, typed UNLOCK confirm
sudroid root [--method magisk|apatch|kernelsu] [--image FILE] [--firmware FILE] [--no-test-boot]
sudroid patch IMAGE [--method magisk] [--out FILE]
sudroid flash IMAGE [--partition boot|init_boot|vendor_boot] [--slot a|b|current]
sudroid verify
sudroid restore [--session ID]
sudroid profiles            support matrix
```

Global options: `--dry-run`, `--yes`, `--serial`, `--json`, `--log-level`,
`--config PATH`, `--no-color`.

Exit codes: 0 ok, 1 generic error, 2 usage, 10 no device, 11 multiple
devices, 12 tool missing, 20 precondition failed, 30 user aborted,
40 patch failed, 50 flash failed.

## 5. Detection

Inputs: `adb shell getprop` full dump, `fastboot getvar all` when in
bootloader, `adb shell ls -l /dev/block/by-name` when readable.

Derived fields on `Device`:

| field | source |
|---|---|
| serial, model, brand, manufacturer, codename | ro.serialno, ro.product.model, ro.product.brand, ro.product.manufacturer, ro.product.device |
| android, sdk, first_api_level, build_id, fingerprint, security_patch | ro.build.version.release, ro.build.version.sdk, ro.product.first_api_level, ro.build.id, ro.build.fingerprint, ro.build.version.security_patch |
| soc | ro.soc.manufacturer, ro.soc.model, ro.hardware, ro.board.platform, ro.hardware.chipname |
| ab, slot | ro.boot.slot_suffix, ro.build.ab_update, fastboot current-slot |
| has_init_boot | by-name listing, fastboot has-slot:init_boot, first_api_level >= 33 heuristic |
| has_vendor_boot | by-name listing, fastboot getvar |
| patch_target | init_boot if has_init_boot and stock boot has no ramdisk, else boot |
| lock | ro.boot.verifiedbootstate (green/orange/yellow/red), ro.boot.flash.locked, ro.boot.vbmeta.device_state, fastboot unlocked, Samsung ro.boot.warranty_bit and knox state |
| oem_unlock_allowed | sys.oem_unlock_allowed |
| encryption | ro.crypto.state, ro.crypto.type |
| dynamic_partitions | ro.boot.dynamic_partitions |
| vendor_profile | registry.profile_for |
| root_present | which su, magisk -v, ksud, apd, /data/adb presence when readable |
| battery | dumpsys battery level |

Vendor detection order: manufacturer, then brand, then SoC vendor for
MediaTek/Unisoc hints on generic devices.

## 6. Vendor profiles

```python
class VendorProfile(Protocol):
    name: str
    flash_backend: FlashBackend          # FASTBOOT, HEIMDALL, ODIN_TAR
    def unlock_steps(self, d: Device) -> list[str]
    def unlock_command(self, d: Device) -> list[str] | None
    def pre_unlock_data(self, d: Device, fb: FastbootClient) -> str | None
    def patch_target(self, d: Device) -> PatchTarget
    def quirks(self, d: Device) -> list[Quirk]
```

| vendor | unlock | flash | notes |
|---|---|---|---|
| Google | `fastboot flashing unlock` | fastboot | init_boot on Pixel 7 and newer, test-boot on boot targets |
| OnePlus | `fastboot oem unlock` | fastboot | some models init_boot on Android 13+ launch |
| Motorola | `fastboot oem get_unlock_data`, user gets key from Motorola site, `fastboot oem unlock KEY` | fastboot | tool prints unlock data and waits for key |
| Sony | code from Sony developer site by IMEI, `fastboot oem unlock 0xCODE` | fastboot | tool prints IMEI, waits for code, warns about DRM key loss |
| Xiaomi | Mi Unlock (Windows) with account binding and wait period | fastboot | tool detects `ro.secureboot.lockstate`, cannot automate unlock, guides |
| ASUS | ASUS unlock app or fastboot on older models | fastboot | guide |
| Nothing | `fastboot flashing unlock` | fastboot | init_boot on newer models |
| Samsung | OEM unlock toggle, download mode, on-device unlock | heimdall, fallback odin_tar | no fastboot, AP tar patch, vbmeta patch, KG/RMM lock detection |
| generic | `fastboot flashing unlock` then `fastboot oem unlock` | fastboot | MediaTek: mtkclient hint; Unisoc: hint; no shortened links |

## 7. Root pipeline

Steps in `workflow/steps.py`, executed by the engine, each with
`check()`, `run()`, `undo()`:

1. `CheckHostTools` adb, fastboot, heimdall (Samsung), magiskboot ready.
2. `CheckDevice` exactly one device, authorized, `Device` detected.
3. `CheckBattery` level >= config min (default 50).
4. `CheckLock` bootloader unlocked, else offer `unlock` flow.
5. `AcquireStockImage` in order: `--image`, `--firmware` archive, rooted
   `dd` pull if root already present, Pixel auto-fetch, else prompt.
6. `BackupStock` save stock image plus manifest to backup dir.
7. `PatchImage` Magisk: extract `libmagiskboot.so` for host arch from
   Magisk APK, run ported `boot_patch` flow (unpack, ramdisk cpio edits,
   config with KEEPVERITY, KEEPFORCEENCRYPT, PATCHVBMETAFLAG, RECOVERYMODE,
   repack, verify). APatch/KernelSU: require user-supplied patched image.
8. `TestBoot` only if target is boot and vendor allows: `fastboot boot`
   patched image, wait for adb, check `su -c id` or `magisk -v`. Skipped
   with `--no-test-boot`.
9. `Flash` fastboot `flash <target><slot_suffix>` or heimdall
   `flash --BOOT/--INIT_BOOT` or emit Odin tar and print steps.
10. `Reboot` and `adb wait-for-device`, no fixed sleeps, timeout 180s.
11. `InstallApp` Magisk/APatch/KernelSU manager APK via `adb install -r`.
12. `Verify` root check, write session manifest, print summary.

Undo per step: flash undo reflashes stock image from backup; unlock has
no undo; patch undo deletes temp files.

Session state: `~/.local/share/sudroid/sessions/<serial>/<timestamp>.json`
(platformdirs on Windows/macOS). `--resume` picks last incomplete session.

## 8. Samsung flow detail

1. Detect via manufacturer. Check OEM unlock toggle state and KG/RMM
   prenormal state from props; if RMM locked, explain 7 day wait.
2. Stock image: user provides AP tar (or tar.md5). Extract
   `boot.img.lz4`, `init_boot.img.lz4` if present, `vbmeta.img.lz4`.
   Decompress with lz4 (Python `lz4` package).
3. Patch boot or init_boot with magiskboot as in section 7. Patch vbmeta
   with disabled verification and verity flags (magiskboot flow with
   PATCHVBMETAFLAG).
4. Output: `magisk_patched.tar` containing patched images re-compressed
   with lz4 legacy frame and proper tar names.
5. Flash: if Heimdall present and device in download mode, `heimdall
   flash --BOOT boot.img [--INIT_BOOT init_boot.img] --VBMETA vbmeta.img`
   with partition names verified against `heimdall print-pit`. Else print
   exact Odin steps (AP slot, uncheck auto reboot).
6. Post flash: guide through factory reset requirement on first boot
   after unlock, then verify.

## 9. Image sources

- User file: any `.img`.
- Firmware archives: factory zip (nested `image-*.zip`), OTA zip with
  `payload.bin` (payload parser with brotli/xz/zstd/bz2 ops, extract only
  needed partitions), Samsung AP tar.
- Rooted device: `su -c dd if=/dev/block/by-name/<part><slot>`.
- Pixel auto-fetch: parse Google factory image index for device codename
  and build id, download, verify sha256 from page, extract boot/init_boot.
  Requires user acceptance of Google terms shown in tool.

All downloads land in `~/.cache/sudroid/`, with sha256 sidecar files.
Magisk releases: GitHub API with ETag cache, fallback to pinned version
in config, asset sha256 checked when release publishes it, otherwise
the APK zip is validated by structure (contains `lib/<arch>/libmagiskboot.so`
and `assets/boot_patch.sh`).

## 10. Safety rules

- Every device write shows the exact command and needs confirmation
  unless `--yes`. Unlock always needs typed `UNLOCK` even with `--yes`.
- `unlock` refuses without a backup manifest for this serial unless
  `--i-know`.
- `--dry-run` runs detection (read-only) and prints the full plan with
  every command; no writes, no downloads.
- Test-boot before flash where possible.
- Slot-correct flashing on A/B. Never flash `boot` when target is
  `init_boot`.
- Refuse to flash an image whose header partition size or ramdisk shape
  does not match the target.
- No `sudo` package installs. `doctor` prints the distro command instead.
- No shortened or affiliate links anywhere.

## 11. Configuration

`~/.config/sudroid/config.toml` (platformdirs):

```toml
[general]
min_battery = 50
backup_dir = "~/sudroid-backups"
log_level = "info"

[magisk]
channel = "stable"      # stable | beta | canary
pinned_version = ""     # override
keep_verity = true
keep_force_encrypt = true
patch_vbmeta = false
recovery_mode = false

[tools]
adb = ""                # explicit path overrides
fastboot = ""
heimdall = ""
auto_download = true
```

CLI flags override config, config overrides defaults. Environment
`SUDROID_*` for CI.

## 12. Logging

Rich console with levels. Rotating file `~/.local/state/sudroid/sudroid.log`
(platformdirs). `--json` emits one JSON object per event on stdout and
moves human output to stderr. Every subprocess call logged with args,
duration, exit code, truncated output.

## 13. Testing

- Unit tests for detection against fixture prop dumps per device.
- Fake tool clients record calls; workflow tests assert exact command
  sequences for each vendor and target.
- magiskboot integration test gated by env var, downloads real Magisk
  APK and patches a small synthetic boot image built in test.
- Payload and AP tar parsers tested on synthetic archives.
- CLI tests via Typer test runner with `--dry-run`.
- Coverage target 85 percent on `sudroid/` excluding `tools/platform_tools.py`
  network paths.

## 14. Quality and delivery

- `pyproject.toml` with hatchling. Dependencies: typer, rich,
  platformdirs, httpx, lz4, tomli (py<3.11), pydantic-free dataclasses.
- ruff (lint + format), mypy strict, pytest, pre-commit config.
- GitHub Actions: `ci.yml` lint, type, test on ubuntu/macos/windows and
  Python 3.10 to 3.13. `release.yml` on `v*` tag: build sdist/wheel,
  PyPI trusted publishing, PyInstaller one-file binaries per OS, attach
  to release with sha256 file.
- `legacy/` holds v2.0 and v2.1 scripts with a deprecation header.
  Removed in v3.1.
- Docs: README rewrite, `docs/support-matrix.md`, `docs/unlock/<vendor>.md`,
  `docs/troubleshooting.md`, `CHANGELOG.md`, `CONTRIBUTING.md`,
  `SECURITY.md`, `.gitignore`.

## 15. Delivery phases

Each phase is one PR into `main` from a feature branch.

1. Skeleton, config, log, tools layer, detection, profiles, `info`,
   `doctor`, `profiles`, tests, CI.
2. Magisk host patch, backup, `patch`, `flash`, `root` for fastboot
   vendors, test-boot, session engine, `--dry-run`, `--resume`.
3. Samsung: AP tar, lz4, vbmeta, Heimdall, Odin tar. `unlock` for all
   vendors.
4. Image sources: payload.bin, factory zip, Pixel auto-fetch. `restore`,
   `verify`, APatch, KernelSU.
5. Docs, README, legacy move, release workflow, tag v3.0.0.

## 16. Open risks

- magiskboot flags and boot_patch behavior change between Magisk
  releases. Mitigation: pin tested version in config, integration test
  in CI on schedule.
- Heimdall is unreliable on recent Samsung models. Mitigation: Odin tar
  fallback always produced.
- Pixel factory index page format may change. Mitigation: fallback to
  manual `--firmware`.
- Windows adb driver issues are outside tool control. `doctor` prints
  driver guidance.
