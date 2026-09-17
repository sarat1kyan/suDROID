<div align="center">

```
         ____  _____ _____ _____ ____
 ___ _ _|    \| __  |     |     |    \
|_ -| | |  |  |    -|  |  |-   -|  |  |
|___|___|____/|__|__|_____|_____|____/
```

**Root Android from your terminal. Detect, back up, patch, test boot, flash, verify.**

[![ci](https://github.com/sarat1kyan/suDROID/actions/workflows/ci.yml/badge.svg)](https://github.com/sarat1kyan/suDROID/actions/workflows/ci.yml)
[![release](https://img.shields.io/github/v/release/sarat1kyan/suDROID?display_name=tag&sort=semver)](https://github.com/sarat1kyan/suDROID/releases)
[![python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-3776AB)](pyproject.toml)
[![platforms](https://img.shields.io/badge/host-linux%20%7C%20macos%20%7C%20windows-informational)](#install)
[![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)

</div>

---

suDROID is a cross platform CLI that takes an Android phone from stock to rooted with the least
amount of guesswork. It reads the device, picks the right partition and slot, patches with the
exact Magisk build it installs, boots the result from RAM before writing anything, and keeps a
stock backup so it can undo itself.

```
$ sudroid root --firmware panther-up1a.231105.003-factory-33cc44dd.zip

 Device
 Model             google Pixel 7
 Codename          panther
 Android           14 (SDK 34, first API 33)
 Build             UP1A.231105.003
 SoC               tensor Tensor G2
 Kernel            5.10.198-android13-4-00050-g12ab34cd
 A/B               yes, slot a
 Patch target      init_boot
 Bootloader        unlocked
 Root present      none
 Battery           82%

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
...
root verified magisk 28.1:MAGISK
done. session 20260917-181203-4f1a2c
```

## Why v3

The v2 shell scripts patched on the wrong machine, ignored A/B slots and `init_boot`, unlocked
bootloaders without asking, and claimed Samsung support without a Samsung flashing path.
v3 is a rewrite around one idea: **the device tells the tool what to do, not a fixed step list.**

| | v2 scripts | v3 |
|---|---|---|
| Hosts | Linux bash, Windows PowerShell (diverged) | one Python codebase, Linux, macOS, Windows, single file binaries |
| Partition | always `boot` | `boot` or `init_boot` from the partition table, slot aware |
| Patching | ran Android binaries on the host | Magisk's own `boot_patch.sh` on the device, always the same build that gets installed |
| Before writing | nothing | `fastboot boot` test run, root check over adb, then flash |
| Samsung | not possible | AP tar in, Heimdall or Odin tar out, vbmeta handled |
| Unlock | silent `fastboot oem unlock` | vendor specific flow, typed confirmation, backup required |
| Recovery | none | stock backup with manifest, `sudroid restore`, undo on failure, `--resume` |
| Tests | none | 190+ tests, fake device state machine, CI on 3 OS x 4 Python |

## Install

```
pipx install sudroid          # or: pip install sudroid
sudroid doctor                # checks adb, fastboot, heimdall, drivers; downloads platform-tools if missing
```

Single file binaries for Linux (x86_64, arm64), macOS (x86_64, arm64) and Windows are on the
[releases page](https://github.com/sarat1kyan/suDROID/releases). No Python needed.

On the phone: Developer options, enable **USB debugging** and **OEM unlocking**.

## Commands

| Command | What it does |
|---|---|
| `sudroid doctor` | host tools, adb server, udev rules, driver hints |
| `sudroid info` | full device report, `--json` for scripts |
| `sudroid unlock` | bootloader unlock, automated where the vendor allows, guided otherwise |
| `sudroid backup` | save a stock image for this device, `--list` to see them |
| `sudroid root` | the whole pipeline, `--method magisk`, `kernelsu` or `apatch` |
| `sudroid patch IMAGE` | patch with Magisk on the device, flash nothing |
| `sudroid flash IMAGE` | flash any image to the right partition and slot, `--test-boot` first |
| `sudroid verify` | is root working, which solution |
| `sudroid restore` | flash the saved stock image back |
| `sudroid profiles` | vendor support matrix |
| `sudroid config` | effective config, `--init` writes the file |

Global flags: `--dry-run` (every device write is printed, none executed), `--yes`, `--serial`,
`--json`, `--log-level`, `--config`, `--no-color`.

## Getting the stock image

Magisk patches the stock `boot.img` or `init_boot.img` of the **installed build**. suDROID
extracts it for you from whatever the vendor ships:

| Source | Flag | Vendors |
|---|---|---|
| Google factory image, fetched and sha256 checked | `--auto-fetch` | Pixel |
| Factory zip | `--firmware x.zip` | Pixel |
| Full OTA zip (`payload.bin`, parsed in place, only needed partitions extracted) | `--firmware ota.zip` | OnePlus, Nothing, Pixel, most GKI devices |
| Raw `payload.bin` | `--firmware payload.bin` | any |
| Samsung AP tar (`.tar.md5`, lz4 entries) | `--firmware AP_xxx.tar.md5` | Samsung |
| Extracted image | `--image boot.img` | any |
| Already rooted device | nothing, pulled with `dd` | any |

Incremental OTAs are detected and rejected with a message instead of producing a broken image.

## Root methods

**Magisk (default).** The APK's `boot_patch.sh` and native binaries for the device ABI are pushed
to `/data/local/tmp` and run over adb. The patched image is pulled back, sanity checked, test
booted with `fastboot boot` when the target is `boot`, then flashed to the active slot. The same
APK is installed as the manager.

**KernelSU.** `uname -r` gives the KMI (for example `android12-5.10`). The matching prebuilt GKI
boot image from the latest KernelSU release is downloaded, test booted and flashed to `boot`,
then the manager is installed. Non GKI kernels get manual steps.

**APatch.** The manager is installed and the stock image copied to `Download/`. Patch in the app,
then `sudroid flash apatch_patched.img --partition boot --test-boot`.

## Samsung

```
sudroid root --firmware AP_G991BXXU5DVJB_CL25260648_QB58521306_REV00_user_low_ship_MULTI_CERT_meta_OS13.tar.md5
sudroid root --firmware AP_....tar.md5 --odin      # no Heimdall: writes magisk_patched.tar.md5 for Odin
```

`boot.img` or `init_boot.img` and `vbmeta.img` are pulled from the AP tar, the boot image is
patched on the device, vbmeta gets the verification and hashtree disabled flags (the same edit the
Magisk app makes), the phone is rebooted to download mode with `adb reboot download`, partition
names are checked against the PIT and flashed with Heimdall. Without Heimdall the tool writes a
raw image AP tar with the md5 trailer and prints the Odin steps.

Knox trips permanently. US carrier models cannot unlock; the tool detects them and refuses.

## Safety model

- Every device write goes through one code path that is logged, confirmable, dry-runnable and
  undoable. `--dry-run` runs all read steps and prints the exact commands it would run.
- Unlock needs a typed `UNLOCK`, which `--yes` cannot bypass, and a stock backup unless `--i-know`.
- Test boot before flash on every device that supports it. If root does not come up from RAM,
  nothing was written.
- Partition existence is confirmed with `fastboot getvar` before `fastboot flash`. `init_boot`
  is taken from the device partition table, not guessed from the model name.
- Image kind is checked against the target: no vendor_boot into boot, no kernel into init_boot.
- Stock images and vbmeta are saved with a manifest per serial before any write.
  `sudroid restore` puts them back. On failure the engine offers to undo completed writes.
- Sessions are checkpointed. `sudroid root --resume` continues after a cable pull.
- Downloads are sha256 verified where the source publishes a hash. No `sudo`, no shortened links.

## Supported devices

| Vendor | Unlock | Flash | Test boot |
|---|---|---|---|
| Google Pixel | automated | fastboot | boot targets |
| OnePlus, Nothing, generic fastboot | automated | fastboot | yes |
| Motorola | automated with unlock key | fastboot | yes |
| Sony Xperia | automated with unlock code | fastboot | yes |
| Xiaomi, Redmi, POCO | guided (Mi Unlock) | fastboot | yes |
| ASUS | guided | fastboot | yes |
| Samsung | guided (download mode) | Heimdall or Odin tar | no |

Full matrix: [docs/support-matrix.md](docs/support-matrix.md). Unlock guides per vendor:
[docs/unlock](docs/unlock/README.md). Problems: [docs/troubleshooting.md](docs/troubleshooting.md).

## Configuration

`sudroid config --init` writes `~/.config/sudroid/config.toml` (platform equivalent elsewhere).
Every key can be overridden with `SUDROID_<SECTION>_<KEY>`.

```toml
[general]
min_battery = 50
backup_dir = "~/sudroid-backups"
log_level = "info"

[magisk]
channel = "stable"        # stable, beta, canary, debug
pinned_version = ""       # e.g. "v28.1"
keep_verity = true
keep_force_encrypt = true
patch_vbmeta = false
recovery_mode = false

[tools]
adb = ""                  # explicit paths override PATH
fastboot = ""
heimdall = ""
auto_download = true      # fetch Google platform-tools when missing
```

## How it is built

```
cli  ->  commands  ->  workflow engine (check / confirm / run / checkpoint / undo)
                         |
              +----------+-----------+
              |          |           |
            root/     images/     backup/        <- Magisk, KernelSU, APatch; payload.bin,
              |          |           |              factory zip, AP tar; manifests
              +----------+-----------+
                         |
                      device/                     <- props -> Device, vendor profiles
                         |
                      tools/                      <- adb, fastboot, heimdall, platform-tools
                                                     (the only place that spawns processes)
```

Only `tools/` runs subprocesses, behind a `Runner` that tests replace with a scripted fake device
and `--dry-run` wraps to block writes. Detection is a pure function from a getprop dump to an
immutable `Device`. Vendor logic lives in `device/profiles/` and nowhere else.

```
git clone https://github.com/sarat1kyan/suDROID && cd suDROID
uv venv -p 3.12 .venv && uv pip install -p .venv/bin/python -e '.[dev]'
.venv/bin/ruff check . && .venv/bin/mypy && .venv/bin/pytest
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the rules and how to add a device fixture.

## Legacy

The v2.0 and v2.1 scripts live in [`legacy/`](legacy/) for reference. They are unmaintained and
will be removed in 3.1.

## Disclaimer

Rooting voids warranties, trips Knox, erases DRM keys on Sony, and can brick a device when done
wrong. suDROID reduces the ways to do it wrong; it does not remove them. Read the plan it prints,
keep the backup it makes, and understand each step before you confirm it. MIT licensed, provided
as is.
