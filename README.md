<div align="center">

```
         ____  _____ _____ _____ ____
 ___ _ _|    \| __  |     |     |    \
|_ -| | |  |  |    -|  |  |-   -|  |  |
|___|___|____/|__|__|_____|_____|____/
```

### Root Android from your terminal.

**Detect. Back up. Patch. Test boot. Flash. Verify. Undo.**

[![ci](https://github.com/sarat1kyan/suDROID/actions/workflows/ci.yml/badge.svg)](https://github.com/sarat1kyan/suDROID/actions/workflows/ci.yml)
[![release](https://github.com/sarat1kyan/suDROID/actions/workflows/release.yml/badge.svg)](https://github.com/sarat1kyan/suDROID/actions/workflows/release.yml)
[![version](https://img.shields.io/github/v/release/sarat1kyan/suDROID?display_name=tag&sort=semver&color=blue)](https://github.com/sarat1kyan/suDROID/releases/latest)
[![python](https://img.shields.io/badge/python-3.10%20to%203.13-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![hosts](https://img.shields.io/badge/host-linux%20%7C%20macos%20%7C%20windows-informational)](#install)
[![typed](https://img.shields.io/badge/mypy-strict-success)](pyproject.toml)
[![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)

[Install](#install) -
[Quick start](#quick-start) -
[Commands](#commands) -
[Devices](#supported-devices) -
[Stock images](#getting-the-stock-image) -
[Root methods](#root-methods) -
[Samsung](#samsung) -
[Safety](#safety-model) -
[Config](#configuration) -
[Troubleshooting](#troubleshooting) -
[Architecture](#how-it-is-built)

</div>

---

suDROID is a cross platform CLI that takes an Android phone from stock to rooted with the least
amount of guesswork. It reads the device, picks the right partition and slot, patches with the
exact Magisk build it installs, boots the result from RAM before writing anything, and keeps a
stock backup so it can undo itself.

```
$ sudroid root --firmware panther-up1a.231105.003-factory-33cc44dd.zip

 Device
 Model               google Pixel 7
 Codename            panther
 Serial              2A281FDH200PIX
 Vendor profile      Google Pixel
 Android             14 (SDK 34, first API 33)
 Build               UP1A.231105.003
 Security patch      2023-11-05
 SoC                 tensor Tensor G2
 Kernel              5.10.198-android13-4-00050-g12ab34cd
 A/B                 yes, slot a
 Patch target        init_boot
 init_boot           yes
 Bootloader          unlocked
 OEM unlock allowed  yes
 Encryption          encrypted/file
 Root present        none
 Battery             82%
 Flash backend       fastboot
 Test boot           yes

 Plan
  #  Step                                       Writes  State
  1  Check host tools
  2  Check battery
  3  Check bootloader unlocked
  4  Acquire stock init_boot image
  5  Back up stock image
  6  Fetch Magisk
  7  Patch image on device                       yes
  8  Test boot patched image (no write)          yes    skip: init_boot images cannot be test-booted
  9  Flash patched image to init_boot_a          yes
 10  Wait for Android
 11  Install Magisk app                          yes
 12  Verify root

Start rooting? [y/N] y
battery 82%
stock image: stock_init_boot.img header v4 8388608 bytes
backup: /home/me/sudroid-backups/2A281FDH200PIX/20260917-181203-init_boot.img
Magisk 28.1 (stable) for arm64-v8a
Patch image on device
patched: patched_init_boot.img (Magisk 28.1)
Flash patched image to init_boot_a. Continue? [y/N] y
flashed init_boot_a
Wait for Android
Install Magisk app
root verified magisk 28.1:MAGISK
done. session 20260917-181203-4f1a2c
```

## Contents

- [Why v3](#why-v3)
- [Install](#install)
- [Quick start](#quick-start)
- [Commands](#commands)
- [Global flags](#global-flags)
- [Exit codes](#exit-codes)
- [Supported devices](#supported-devices)
- [Getting the stock image](#getting-the-stock-image)
- [Root methods](#root-methods)
- [Samsung](#samsung)
- [Bootloader unlock](#bootloader-unlock)
- [Safety model](#safety-model)
- [Configuration](#configuration)
- [Files and directories](#files-and-directories)
- [Troubleshooting](#troubleshooting)
- [How it is built](#how-it-is-built)
- [Development](#development)
- [FAQ](#faq)
- [Legacy](#legacy)
- [License and disclaimer](#license-and-disclaimer)

## Why v3

The v2 shell scripts patched on the wrong machine, ignored A/B slots and `init_boot`, unlocked
bootloaders without asking, and claimed Samsung support without a Samsung flashing path.
v3 is a rewrite around one idea: **the device tells the tool what to do, not a fixed step list.**

| | v2 scripts | v3 |
|---|---|---|
| Hosts | Linux bash and Windows PowerShell, diverged | one Python codebase, Linux, macOS, Windows, single file binaries |
| Partition | always `boot` | `boot` or `init_boot` from the partition table, slot aware |
| Patching | ran Android binaries on the host | Magisk's own `boot_patch.sh` on the device, same build that gets installed |
| Before writing | nothing | `fastboot boot` test run, root check over adb, then flash |
| Samsung | not possible | AP tar in, Heimdall or Odin tar out, vbmeta handled |
| Unlock | silent `fastboot oem unlock` | vendor specific flow, typed confirmation, backup required |
| Recovery | none | stock backup with manifest, `sudroid restore`, undo on failure, `--resume` |
| Firmware | none | OTA payload.bin, factory zip, AP tar, Pixel auto fetch |
| Tests | none | 190+ tests, fake device state machine, CI on 3 OS x 4 Python |

## Install

**Python package**

```
pipx install sudroid        # isolated, recommended
pip install sudroid         # or plain pip
```

**Single file binary** (no Python needed): download from the
[latest release](https://github.com/sarat1kyan/suDROID/releases/latest), verify against
`SHA256SUMS`, make executable.

| File | Host |
|---|---|
| `sudroid-linux-x86_64` | Linux, Intel/AMD |
| `sudroid-linux-arm64` | Linux, ARM64 (Raspberry Pi 4/5, servers) |
| `sudroid-macos-arm64` | macOS, Apple silicon |
| `sudroid-macos-x86_64` | macOS, Intel |
| `sudroid-windows-x86_64.exe` | Windows 10/11 |

**From source**

```
git clone https://github.com/sarat1kyan/suDROID && cd suDROID
pip install .
```

**Host requirements**

- `adb` and `fastboot`. If missing, `sudroid doctor` downloads Google platform-tools to the cache.
- Samsung only: Heimdall (`apt install heimdall-flash`, `brew install heimdall`, Heimdall Suite on
  Windows) or use `--odin` to produce a tar for Odin.
- Linux: udev rules for your vendor id (`android-sdk-platform-tools-common` on Debian/Ubuntu).
- Windows: Google USB Driver or the vendor driver if `adb devices` shows nothing.

**Phone requirements**

- Developer options: **USB debugging** on, **OEM unlocking** on.
- Battery at 50% or more (configurable).
- The firmware package or stock image for the **installed build** (`sudroid info` prints the build id).

## Quick start

```
sudroid doctor                       # host tools, adb server, drivers
sudroid info                         # what the tool sees; --json for scripts
sudroid --dry-run root --firmware <package>   # full plan, no device writes
sudroid root --firmware <package>    # do it
sudroid verify                       # root status
```

Common scenarios:

| Scenario | Command |
|---|---|
| Pixel, let the tool download the factory image | `sudroid root --auto-fetch` |
| Pixel or any GKI device, you have the full OTA zip | `sudroid root --firmware ota.zip` |
| You already extracted the stock image | `sudroid root --image init_boot.img` |
| Samsung with Heimdall | `sudroid root --firmware AP_xxx.tar.md5` |
| Samsung with Odin on Windows | `sudroid root --firmware AP_xxx.tar.md5 --odin` |
| KernelSU on a GKI kernel | `sudroid root --method kernelsu --image boot.img` |
| APatch | `sudroid root --method apatch --image boot.img`, then `sudroid flash apatch_patched.img --partition boot --test-boot` |
| Flash an image someone else patched | `sudroid flash patched.img --partition boot --test-boot` |
| Bootloader still locked | `sudroid backup --image boot.img` then `sudroid unlock` |
| Cable fell out mid run | `sudroid root --resume` |
| Go back to stock | `sudroid restore` |

## Commands

<details open>
<summary><code>sudroid doctor</code> - check host tools, drivers and adb server</summary>

Reports Python, host OS and arch, adb, fastboot, heimdall (optional), adb server state,
connected devices and their authorization, udev rules on Linux, driver hints on Windows.
Downloads platform-tools when adb or fastboot are missing and `tools.auto_download` is on.
Exit 12 when a required tool is missing.
</details>

<details open>
<summary><code>sudroid info</code> - device report</summary>

Vendor profile, model, codename, serial, Android version and SDK, first API level, build id,
security patch, SoC, kernel release, A/B and active slot, patch target, presence of `init_boot`
and `vendor_boot`, dynamic partitions, bootloader lock state, OEM unlock toggle, encryption,
root presence (Magisk, KernelSU, APatch, plain su), battery, flash backend, test boot support,
Knox warranty bit on Samsung. Vendor notes and warnings follow. `--json` prints everything as one
object with `effective_patch_target` and `quirks`.
</details>

<details open>
<summary><code>sudroid root</code> - the full pipeline</summary>

| Option | Meaning |
|---|---|
| `--method magisk\|kernelsu\|apatch` | root solution, default `magisk` |
| `--image PATH` | stock `boot.img` or `init_boot.img` for the installed build |
| `--firmware PATH` | firmware package: OTA zip, factory zip, `payload.bin`, Samsung AP tar |
| `--auto-fetch` | Pixel: download the factory image for the installed build |
| `--magisk-version vX.Y` | pin a Magisk tag instead of the channel latest |
| `--no-test-boot` | skip the `fastboot boot` test |
| `--skip-backup` | do not save the stock image (not recommended) |
| `--odin` | Samsung: write an Odin tar instead of flashing with Heimdall |
| `--resume` | continue the last incomplete session for this device |

Steps for fastboot vendors: check tools, battery, unlock state; acquire stock image; back it up;
fetch Magisk; patch on device; test boot (boot targets); flash to the active slot; wait for
Android; install the manager; verify. Every step prints before it runs, every write asks unless
`--yes`. The plan table shows what will be skipped and why.
</details>

<details>
<summary><code>sudroid unlock</code> - bootloader unlock</summary>

Prints the vendor steps and reference link, refuses when OEM unlocking is off, requires a stock
backup for this serial unless `--i-know`, then asks for the typed word `UNLOCK` (not bypassed by
`--yes`). Google, OnePlus, Nothing and generic devices: `fastboot flashing unlock` or
`fastboot oem unlock`. Motorola: runs `fastboot oem get_unlock_data`, prints the string for the
Motorola site, asks for the key, runs `fastboot oem unlock KEY`. Sony: asks for the code from the
Sony developer site, runs `fastboot oem unlock 0xCODE`. Xiaomi, Samsung, ASUS: guided only.
Wipes the device.
</details>

<details>
<summary><code>sudroid backup</code> - save or list stock images</summary>

| Option | Meaning |
|---|---|
| `--image PATH` | register this stock image for the connected device |
| `--partition boot\|init_boot\|vendor_boot` | override the detected target |
| `--list` | show backups for this device with checksum status, `--json` available |

Without `--image` the image is pulled with `dd` when the device is already rooted. Backups are
copied to `general.backup_dir/<serial>/` with a `manifest.json` holding model, build id,
fingerprint, slot, sha256 and source.
</details>

<details>
<summary><code>sudroid patch IMAGE</code> - patch with Magisk, flash nothing</summary>

| Option | Meaning |
|---|---|
| `--out PATH` | where to put the patched image |
| `--magisk-version vX.Y` | pin a Magisk tag |

Needs a connected device: patching runs there with the APK's own script and binaries for the
device ABI.
</details>

<details>
<summary><code>sudroid flash IMAGE</code> - flash any image to the right place</summary>

| Option | Meaning |
|---|---|
| `--partition boot\|init_boot\|vendor_boot\|vbmeta` | default: detected patch target |
| `--slot a\|b\|current` | default `current` |
| `--test-boot` | `fastboot boot` first (boot partition only) |

Refuses when the image kind does not match the partition (vendor_boot into boot, a kernel into
init_boot), and when the partition does not exist on the device.
</details>

<details>
<summary><code>sudroid verify</code> - root status</summary>

Runs `su -c id`, then `magisk -v`, `ksud -V`, `apd -V`, and shows which solution answers.
</details>

<details>
<summary><code>sudroid restore</code> - back to stock</summary>

| Option | Meaning |
|---|---|
| `--partition NAME` | default: detected patch target |
| `--backup ID` | a specific backup id from `sudroid backup --list` |

Picks the latest backup for the installed build (falls back to the latest for the partition
with a warning), verifies its checksum, flashes it.
</details>

<details>
<summary><code>sudroid profiles</code> and <code>sudroid config</code></summary>

`profiles` prints the vendor support matrix (`--json` available). `config` prints the effective
configuration and its file path; `config --init` writes a default file.
</details>

## Global flags

| Flag | Effect |
|---|---|
| `--dry-run` | run every read step, print every device write as the exact command, execute none |
| `--yes`, `-y` | assume yes on confirmations (never on the typed `UNLOCK`) |
| `--serial ID`, `-s ID` | pick a device when several are connected |
| `--json` | machine readable stdout, human output moves to stderr |
| `--log-level LEVEL` | `debug`, `info`, `warning`, `error` |
| `--config PATH` | alternate `config.toml` |
| `--no-color` | plain output |
| `--version` | print version |

## Exit codes

| Code | Meaning |
|---|---|
| 0 | ok |
| 1 | unexpected error |
| 2 | usage |
| 10 | no device |
| 11 | multiple devices, pass `--serial` |
| 12 | required host tool missing |
| 20 | precondition failed (locked, low battery, no stock image, unauthorized, incremental OTA) |
| 30 | aborted by user |
| 40 | patch failed |
| 50 | flash failed or refused |

Every error prints a one line cause and a `hint:` line with the next thing to try.

## Supported devices

| Vendor | Unlock | Flash | Test boot | Notes |
|---|---|---|---|---|
| Google Pixel | automated | fastboot | boot targets | Pixel 7 and later use `init_boot`; `--auto-fetch` |
| OnePlus | automated | fastboot | yes | OxygenOS 14+: use the full OTA zip |
| Nothing | automated | fastboot | yes | `init_boot` on newer models |
| Generic fastboot | automated attempt | fastboot | yes | MediaTek: mtkclient hint, Unisoc: token hint |
| Motorola | automated with unlock key | fastboot | yes | tool prints `get_unlock_data` |
| Sony Xperia | automated with unlock code | fastboot | yes | unlock erases DRM keys |
| Xiaomi, Redmi, POCO | guided (Mi Unlock on Windows) | fastboot | yes | account binding wait |
| ASUS | guided | fastboot | yes | unlock app discontinued for some models |
| Samsung | guided (download mode) | Heimdall or Odin tar | no | Knox trips, US carrier models cannot unlock |

Full matrix with stock image sources: [docs/support-matrix.md](docs/support-matrix.md).
Per vendor unlock guides: [docs/unlock](docs/unlock/README.md).

Detection is data driven, so a device outside this list still gets the right partition, slot and
generic fastboot flow. Add a getprop dump under `tests/fixtures/getprop/` to pin its behaviour.

## Getting the stock image

Magisk patches the stock `boot.img` or `init_boot.img` of the **installed build**. suDROID
extracts it from whatever the vendor ships and keeps `vbmeta.img` when present:

| Source | Flag | Typical for |
|---|---|---|
| Google factory image, fetched from the Google page and sha256 checked | `--auto-fetch` | Pixel |
| Factory zip (nested `image-*.zip`) | `--firmware x.zip` | Pixel |
| Full OTA zip: `payload.bin` parsed in place, only needed partitions extracted | `--firmware ota.zip` | OnePlus, Nothing, Pixel, most GKI devices |
| Raw `payload.bin` | `--firmware payload.bin` | any |
| Samsung AP tar, `.tar` or `.tar.md5`, lz4 entries | `--firmware AP_xxx.tar.md5` | Samsung |
| Extracted image | `--image boot.img` | Xiaomi fastboot ROMs, anything else |
| Already rooted device | nothing, pulled with `dd` | re-rooting after an update |

The payload reader understands `REPLACE`, `REPLACE_BZ`, `REPLACE_XZ` and `ZERO` operations and
checks every blob and partition hash. Incremental OTAs are rejected with a message instead of
producing a broken image. Archives are never fully extracted; a 3 GB factory zip yields a 8 MB
image.

## Root methods

**Magisk (default).** The APK for the chosen channel (`stable`, `beta`, `canary`, `debug`, or a
pinned tag) is downloaded once and cached. Its `boot_patch.sh`, `util_functions.sh`, `stub.apk`
and the native binaries for the device ABI are pushed to `/data/local/tmp/sudroid` and run over
adb with `KEEPVERITY`, `KEEPFORCEENCRYPT`, `PATCHVBMETAFLAG`, `RECOVERYMODE` from the config.
The patched image is pulled back, header checked, test booted with `fastboot boot` when the target
is `boot`, then flashed to the active slot. The same APK is installed as the manager.

**KernelSU.** `uname -r` gives the KMI (for example `5.10.209-android12-9` is `android12-5.10`).
The matching prebuilt GKI boot image from the latest KernelSU release is downloaded together with
the manager APK, test booted, flashed to `boot` (also on `init_boot` devices, as KernelSU lives in
the kernel), and the manager installed. Non GKI kernels get manual steps.

**APatch.** The latest manager is installed and the stock image copied to `Download/`. Patch in the
app with your SuperKey, copy the result back, then
`sudroid flash apatch_patched.img --partition boot --test-boot`.

## Samsung

```
sudroid root --firmware AP_S911BXXS3AWK1_CL26543210_QB70123456_REV00_user_low_ship_MULTI_CERT_meta_OS14.tar.md5
sudroid root --firmware AP_....tar.md5 --odin      # no Heimdall: writes magisk_patched.tar.md5 for Odin
```

1. `boot.img` or `init_boot.img` and `vbmeta.img` are pulled from the AP tar (lz4 frames decoded).
2. The boot image is patched on the device with Magisk's script, exactly as above.
3. `vbmeta.img` gets the verification and hashtree disabled flags at offset 0x78 set to 3, the
   same edit the Magisk app makes when it patches an AP tar.
4. Both stock images are saved to the backup dir.
5. `adb reboot download`, then `heimdall print-pit` confirms `BOOT` / `INIT_BOOT` / `VBMETA`
   exist, then `heimdall flash --INIT_BOOT ... --VBMETA ...`.
6. With `--odin`, or when Heimdall is missing, a raw image AP tar with the md5 trailer is written
   to the work dir and the Odin steps are printed. Flash it, then `sudroid verify`.

Knox trips permanently: Samsung Pay, Secure Folder and Knox features stop working. US carrier
variants (`SM-xxxxU`, `U1`, `W`) have no OEM unlocking; the tool detects them and refuses. If OEM
unlocking is missing from Developer options, the KG/RMM state needs 7 days with a SIM and internet.

## Bootloader unlock

`sudroid unlock` handles the whole thing for vendors that allow it and prints exact steps for
the rest. Unlocking wipes the device, disables USB debugging and requires setup again. After
the wipe: finish setup, re-enable USB debugging and OEM unlocking, then run `sudroid root`.

| Vendor | Flow |
|---|---|
| Google, Nothing | `fastboot flashing unlock`, confirm on the phone |
| OnePlus, generic | `fastboot oem unlock`, then `fastboot flashing unlock` as fallback |
| Motorola | tool prints unlock data, you paste it on the Motorola site, tool sends the key |
| Sony | you request the code with your IMEI, tool sends `fastboot oem unlock 0xCODE` |
| Xiaomi | Mi Unlock Tool on Windows after account binding, 72 hours to 30 days |
| Samsung | download mode, long press Volume Up, unlock menu |
| ASUS | ASUS unlock app for the model, or fastboot on older models |

Guides with the phone side steps: [docs/unlock](docs/unlock/README.md).

## Safety model

- **One write path.** Every device write goes through the workflow engine: logged, confirmable,
  dry-runnable, checkpointed, undoable. Only `sudroid/tools/` spawns processes and every write
  is flagged, so `--dry-run` cannot miss one.
- **Test boot before flash** wherever the device allows it. If root does not come up from the RAM
  boot, nothing was written and a power cycle returns stock.
- **Partition truth from the device.** `init_boot` comes from the partition table over adb; the
  launch API heuristic is only a fallback and is re-checked with `fastboot getvar` before writing.
  The active slot is read from fastboot right before the flash.
- **Image sanity.** Header magic, header version, kernel and ramdisk sizes are checked. No
  `vendor_boot` into `boot`, no kernel into `init_boot`, no flashing of an unknown blob.
- **Backups first.** Stock images and vbmeta are saved with a manifest per serial before any
  write. `sudroid restore` puts them back. On failure the engine offers to undo completed writes.
- **Unlock friction on purpose.** Typed `UNLOCK`, refused without a backup unless `--i-know`,
  refused when OEM unlocking is off, refused on US Samsung variants.
- **Sessions.** Each run writes a JSON checkpoint after every step. `--resume` continues.
- **Verified downloads.** Factory images against the sha256 on Google's page, Magisk APK against
  a cached checksum and structure check, GitHub releases through the API with ETag caching.
- **No `sudo`, no shortened links, no telemetry.**

## Configuration

`sudroid config --init` writes the file, `sudroid config` shows the effective values. Precedence:
defaults, then the file, then `SUDROID_<SECTION>_<KEY>` environment variables, then flags.

```toml
[general]
min_battery = 50                # percent required before rooting
backup_dir = "~/sudroid-backups"
log_level = "info"

[magisk]
channel = "stable"              # stable, beta, canary, debug
pinned_version = ""             # e.g. "v28.1", overrides channel
keep_verity = true              # KEEPVERITY for boot_patch.sh
keep_force_encrypt = true       # KEEPFORCEENCRYPT
patch_vbmeta = false            # PATCHVBMETAFLAG
recovery_mode = false           # RECOVERYMODE, old Samsung system-as-root

[tools]
adb = ""                        # explicit paths override PATH lookup
fastboot = ""
heimdall = ""
auto_download = true            # fetch Google platform-tools when missing
```

Examples: `SUDROID_GENERAL_MIN_BATTERY=30`, `SUDROID_MAGISK_CHANNEL=canary`,
`SUDROID_TOOLS_AUTO_DOWNLOAD=false`.

## Files and directories

| What | Linux | macOS | Windows |
|---|---|---|---|
| config | `~/.config/sudroid/config.toml` | `~/Library/Application Support/sudroid/config.toml` | `%LOCALAPPDATA%\sudroid\config.toml` |
| cache (platform-tools, Magisk APKs, factory images, releases) | `~/.cache/sudroid/` | `~/Library/Caches/sudroid/` | `%LOCALAPPDATA%\sudroid\Cache\` |
| log (rotating, debug level) | `~/.local/state/sudroid/sudroid.log` | `~/Library/Application Support/sudroid/sudroid.log` | `%LOCALAPPDATA%\sudroid\sudroid.log` |
| sessions and work dirs | `~/.local/share/sudroid/sessions/<serial>/`, `.../work/<session>/` | `~/Library/Application Support/sudroid/...` | `%LOCALAPPDATA%\sudroid\...` |
| backups | `~/sudroid-backups/<serial>/manifest.json` and `*.img` (configurable) | same | same |

Work dirs hold the stock, patched and Odin tar files for a session. Safe to delete after a
successful run; backups are elsewhere.

## Troubleshooting

| Symptom | What to do |
|---|---|
| `no device found` | USB debugging on, data cable, accept the RSA prompt, `sudroid doctor` |
| `device is unauthorized` | accept the prompt on the phone; revoke authorizations and retry if it does not appear |
| `bootloader state is locked` | `sudroid unlock` |
| `no stock image available` | `--firmware` with the package for the installed build, `--image`, or `--auto-fetch` on Pixel |
| `this is an incremental OTA` | download the full OTA or the factory image |
| `init_boot_a not present on device` | the partition table was unreadable and the guess was wrong; pass `--image boot.img` |
| test boot hangs on the logo | nothing was written; hold Power 10 s; try `channel = "canary"` or `keep_verity = false` |
| bootloop after flash | `sudroid restore`; enter the bootloader manually if adb is gone |
| Heimdall does not detect | USB 2.0 port, other cable, remove Kies/Smart Switch drivers, or `--odin` |
| `Failed to detect compatible download-mode device` after unlock | finish first boot with internet so VaultKeeper releases the bootloader |

More in [docs/troubleshooting.md](docs/troubleshooting.md). Attach the log file and
`sudroid --json info` when opening an issue; strip the serial if you want.

## How it is built

```
cli  ->  commands  ->  workflow engine (check / confirm / run / checkpoint / undo)
                         |
              +----------+-----------+
              |          |           |
            root/     images/     backup/        <- Magisk, KernelSU, APatch; payload.bin,
              |          |           |              factory zip, AP tar, Pixel fetch; manifests
              +----------+-----------+
                         |
                      device/                     <- getprop -> Device, vendor profiles
                         |
                      tools/                      <- adb, fastboot, heimdall, platform-tools
                                                     (the only place that spawns processes)
```

- `tools/` wraps subprocesses behind a `Runner`. Tests inject a scripted fake device, `--dry-run`
  wraps the real runner and blocks anything flagged as a write.
- `device/detect.py` is a pure function from a getprop dump and fastboot vars to an immutable
  `Device`. Everything downstream reads that object, never raw props.
- `device/profiles/` holds all vendor specific behaviour: unlock steps and commands, flash
  backend, patch target, quirks. Nothing else branches on vendor.
- `workflow/engine.py` runs typed steps with `skip`, `check`, `run`, `undo`, writes a session
  checkpoint after each, and gates mutating steps behind confirmation and dry-run.
- `images/payload.py` is a 300 line protobuf wire decoder for update_engine manifests. No
  generated code, no protobuf dependency.

Dependencies: typer, rich, httpx, platformdirs, lz4. Standard library for zip, tar, bz2, lzma,
hashing and the boot header parsing.

## Development

```
git clone https://github.com/sarat1kyan/suDROID && cd suDROID
uv venv -p 3.12 .venv && uv pip install -p .venv/bin/python -e '.[dev]'
.venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/mypy && .venv/bin/pytest
```

- ruff, mypy strict, pytest with a 60 s per test timeout. CI runs the matrix on every PR.
- End to end tests drive the CLI against `tests/flow_helpers.py`, a fake device with a mode state
  machine (android, bootloader, download) that records every flash and boot.
- Add a device family by dropping a getprop dump under `tests/fixtures/getprop/` and, if needed, a
  profile under `sudroid/device/profiles/`.
- Releases: tag `vX.Y.Z` on `main`. The workflow runs the checks, builds sdist and wheel, five
  PyInstaller binaries with sha256 files, and publishes the GitHub release with the matching
  changelog section. PyPI publishing runs when the `PYPI_TRUSTED_PUBLISHING` repository variable
  is `true`.

See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

## FAQ

**Does it work without a stock image?** Only when the device is already rooted (it pulls the
partition with `dd`). Otherwise you need the firmware package for the installed build. Pixel can
fetch it automatically.

**Why patch on the device instead of on my computer?** The Magisk APK ships Android binaries, not
host binaries. Running the APK's own script on the phone means the patch logic always matches the
Magisk version being installed and works the same from Linux, macOS and Windows.

**Can I use it after an OTA update to re-root?** Yes: `sudroid root --firmware <new full OTA>`.
The tool sees the new build id and patches the new stock image. Backups are kept per build.

**Will Play Integrity pass?** Not the tool's job. Magisk modules (Zygisk, hide lists) handle that;
`sudroid verify` only reports root.

**Does `--dry-run` need a device?** Yes, it still reads the device to build a real plan. It never
writes.

**Windows and Heimdall?** Heimdall Suite works on many models; when it does not, `--odin` gives
you a tar for Odin.

## Legacy

The v2.0 and v2.1 scripts live in [`legacy/`](legacy/) for reference. They are unmaintained,
have the defects listed under [Why v3](#why-v3), and will be removed in 3.1.

## License and disclaimer

MIT, see [LICENSE](LICENSE). Changelog in [CHANGELOG.md](CHANGELOG.md).

Rooting voids warranties, trips Knox, erases DRM keys on Sony, and can brick a device when done
wrong. suDROID reduces the ways to do it wrong; it does not remove them. Read the plan it prints,
keep the backup it makes, and understand each step before you confirm it. Provided as is.
