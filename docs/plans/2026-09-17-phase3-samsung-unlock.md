# Phase 3: Samsung and Unlock Implementation Plan

**Goal:** `sudroid root` works on Samsung via Heimdall, falls back to an Odin tar. `sudroid unlock` drives or guides bootloader unlock for every vendor profile.

**Architecture:** Samsung stock images come from the AP firmware tar (`--firmware AP_*.tar.md5`), entries are lz4 frame compressed. Patching still runs on the booted device with Magisk's script. vbmeta is patched on the host by setting AVB flags to 3 at offset 0x78, which is what the Magisk app does for Samsung tars. Flashing: `adb reboot download`, `heimdall detect`, `heimdall flash --BOOT ... --INIT_BOOT ... --VBMETA ...` with partition names confirmed from `heimdall print-pit`. Without Heimdall the tool writes an Odin AP tar with raw images and prints the Odin steps. Root steps become profile dependent.

**Tech Stack:** `lz4` (frame decompress), `tarfile`, existing engine.

**Spec:** `docs/specs/2026-09-17-sudroid-v3-design.md` sections 6, 8.

---

### Task 1: Heimdall client

**Files:** `sudroid/tools/heimdall.py`, `tests/test_heimdall.py`

```python
class HeimdallClient:
    def __init__(self, runner, path="heimdall")
    def version(self) -> str
    def detect(self) -> bool                       # exit 0 when a device in download mode is present
    def print_pit(self) -> list[str]               # partition names from "Partition Name: X" lines, --no-reboot
    def flash(self, images: dict[str, Path], *, no_reboot=False) -> Result   # --NAME path ..., mutating
    def wait(self, timeout=120) -> bool
```

### Task 2: Samsung firmware archive

**Files:** `sudroid/images/samsung.py`, `tests/test_samsung_images.py`

```python
AP_IMAGES = ("boot.img", "init_boot.img", "vbmeta.img", "recovery.img")
def list_ap(tar_path: Path) -> list[str]
def extract_ap(tar_path: Path, dest: Path, names=AP_IMAGES) -> dict[str, Path]
    # handles .tar and .tar.md5 (trailing md5 line), entries X.img or X.img.lz4 (lz4 frame), streaming, size guard 512 MB per entry
def build_odin_tar(images: dict[str, Path], out: Path) -> Path
    # raw .img entries, ustar, names boot.img / init_boot.img / vbmeta.img, mode 0644, plus .md5 sidecar file "<out>.md5" = md5 of tar + "  name" appended as Odin expects (tar.md5 = tar bytes + md5 line)
```
Tests: synthetic tar with lz4-compressed and raw entries, md5 suffix, extract, rebuild, verify md5 trailer.

### Task 3: Samsung steps and profile-aware root

**Files:** `sudroid/workflow/steps.py` (add), `sudroid/workflow/samsung_steps.py`, `sudroid/commands/root.py`, `sudroid/cli.py` (`--firmware`)

Steps:
- `AcquireImage`: accept `data["firmware"]`; for Samsung extract target image and vbmeta to work; `data["vbmeta"]`. For fastboot vendors `--firmware` reports "firmware archive support for this vendor arrives in the next release" (payload.bin in phase 4).
- `PatchVbmeta`: patch flags, write `patched_vbmeta.img`, skip when no vbmeta in session.
- `EnterDownloadMode` (mutating): `adb reboot download`, `heimdall.wait`.
- `HeimdallFlash` (mutating): print-pit names must include BOOT/INIT_BOOT/VBMETA as needed, flash dict, undo flashes stock images from backup.
- `OdinTarOut`: when heimdall missing: build tar into work dir, print Odin steps, raise PreconditionError exit 20 with path (root stops here; user flashes manually, then runs `sudroid verify`).
- `root_steps(profile)` picks fastboot or Samsung list. Remove `CheckBackend` block for Samsung.
- `CheckTools`: Samsung requires heimdall unless `--odin` flag -> data["odin"]="1".

### Task 4: unlock command

**Files:** `sudroid/commands/unlock.py`, `sudroid/cli.py`, `tests/test_unlock_cmd.py`

Flow:
1. detect device, profile. If unlocked: print and exit 0.
2. print `unlock_steps`, url, quirks.
3. if `oem_unlock_allowed is False`: PreconditionError "enable OEM unlocking in Developer options".
4. if not `unlock_automatable`: print steps, exit 0 (guided).
5. unless `--i-know`: require `BackupManager.has_backup(serial)` else PreconditionError with hint `sudroid backup --image`.
6. `typed_confirm("UNLOCK", "This wipes all data on <model>")` (never bypassed by --yes).
7. reboot to bootloader, wait.
8. Motorola: `oem_read get_unlock_data`, print joined data, prompt for key, `oem unlock KEY`. Sony: prompt for code, `oem unlock 0xCODE`. Others: try `unlock_commands` in order until one returns ok or `getvar unlocked` == yes.
9. reboot, print "device wipes and reboots; re-enable USB debugging, then run sudroid root".
Tests with FakeDevice: pixel5 locked with backup -> flashing unlock issued; without backup -> exit 20; typed word mismatch -> exit 30; xiaomi -> guided exit 0 no mutating calls; motorola -> get_unlock_data then oem unlock KEY.

### Task 5: PR
