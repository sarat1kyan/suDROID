# Phase 2: Root Pipeline Implementation Plan

**Goal:** `sudroid root` works end to end on fastboot vendors: acquire stock image, back up, patch with Magisk, test-boot, flash to the right slot, install app, verify. Plus `backup`, `patch`, `flash`, `verify` commands, session engine with resume, dry-run.

**Architecture:** Magisk patching runs on the device: the tool extracts `boot_patch.sh`, `util_functions.sh`, `stub.apk` and the device ABI's `lib*.so` from the Magisk APK, pushes them to `/data/local/tmp/sudroid`, runs the script over adb, pulls `new-boot.img`. This uses Magisk's own patch logic for the exact version being installed and needs no host binaries. A workflow engine runs typed steps with check/run/undo, writes a session checkpoint after each step, and gates mutating steps behind confirmations and dry-run.

**Tech Stack:** httpx (Magisk channel JSON + APK), zipfile, hashlib, dataclasses, existing tools layer.

**Spec:** `docs/specs/2026-09-17-sudroid-v3-design.md` sections 7, 9, 10.

## Global Constraints

- Same as phase 1. Every device write is `mutating=True`.
- No fixed sleeps for device state. Poll `adb devices` / `fastboot devices` with timeouts.
- Downloads go to `paths.cache_dir()` with `.sha256` sidecar.
- Never flash `boot` when the effective patch target is `init_boot`.

---

### Task 1: Device ABI and boot image inspection

**Files:** `sudroid/device/model.py` (add `abi: str`), `sudroid/device/detect.py`, `sudroid/images/__init__.py`, `sudroid/images/verify.py`, `tests/test_images_verify.py`

**Interfaces:**
```python
# Device gains: abi: str  (ro.product.cpu.abi, e.g. arm64-v8a)

@dataclass(frozen=True)
class ImageInfo:
    path: Path; size: int; sha256: str
    kind: str            # "boot", "vendor_boot", "unknown"
    header_version: int  # -1 when unknown
    kernel_size: int; ramdisk_size: int
    @property has_ramdisk -> bool

def inspect(path: Path) -> ImageInfo
def sha256_file(path: Path) -> str
def patch_vbmeta_flags(data: bytes) -> bytes   # set flags |= 3 at offset 0x78 when magic AVB0
```
Boot header: magic `ANDROID!` at 0, kernel_size u32 LE at 8, ramdisk_size at 12, header_version at 40 (all versions). `VNDRBOOT` magic for vendor_boot. Tests build synthetic headers.

### Task 2: Magisk releases and APK extraction

**Files:** `sudroid/root/__init__.py`, `sudroid/root/releases.py`, `sudroid/root/apk.py`, `tests/test_releases.py`, `tests/test_apk.py`

**Interfaces:**
```python
CHANNEL_URLS = {"stable": "https://github.com/topjohnwu/magisk-files/raw/master/stable.json",
                "beta": ".../beta.json", "canary": ".../canary.json"}
@dataclass(frozen=True)
class MagiskRelease: version: str; version_code: int; apk_url: str; channel: str
def fetch_release(client, channel="stable", pinned="") -> MagiskRelease
    # pinned "v27.0" -> https://github.com/topjohnwu/Magisk/releases/download/v27.0/Magisk-v27.0.apk
def download_apk(client, rel, cache: Path) -> Path      # skips when file + .sha256 sidecar present
def validate_apk(path: Path) -> None                     # raises PatchError unless assets/boot_patch.sh and lib/*/libmagiskboot.so exist

@dataclass(frozen=True)
class MagiskBundle: dir: Path; version: str; abi: str; files: tuple[str, ...]
def extract_bundle(apk: Path, abi: str, dest: Path) -> MagiskBundle
    # assets/*.sh, assets/stub.apk -> dest/; lib/<abi>/libX.so -> dest/X (strip lib prefix and .so)
    # abi fallback: arm64-v8a -> also needs armeabi-v7a magisk32 when present: copy lib/armeabi-v7a/libmagisk*.so as magisk32 if lib/<abi>/ has no magisk32
```
Tests: MockTransport channel JSON; synthetic APK zip.

### Task 3: Device-side patcher

**Files:** `sudroid/root/device_patch.py`, `tests/test_device_patch.py`

**Interfaces:**
```python
REMOTE_DIR = "/data/local/tmp/sudroid"
@dataclass
class PatchOptions: keep_verity=True; keep_force_encrypt=True; patch_vbmeta=False; recovery_mode=False; legacy_sar=False
@dataclass(frozen=True)
class PatchResult: image: Path; magisk_version: str; log: str
class DevicePatcher:
    def __init__(self, adb: AdbClient, bundle: MagiskBundle)
    def patch(self, stock: Path, out: Path, opts: PatchOptions) -> PatchResult
```
Sequence (all via adb): `shell rm -rf REMOTE_DIR; mkdir -p REMOTE_DIR` (mutating), push each bundle file, push stock as `REMOTE_DIR/stock.img`, `shell chmod -R 755 REMOTE_DIR`, `shell cd REMOTE_DIR && KEEPVERITY=true KEEPFORCEENCRYPT=true PATCHVBMETAFLAG=false RECOVERYMODE=false LEGACYSAR=false sh ./boot_patch.sh ./stock.img` (mutating, timeout 300), check exit and that output lacks `! ` abort markers, `pull REMOTE_DIR/new-boot.img out`, `shell rm -rf REMOTE_DIR`. Raise PatchError with tail of script output on failure. Verify pulled image with `inspect` (kind boot, has_ramdisk).

### Task 4: Backup manager

**Files:** `sudroid/backup/__init__.py`, `sudroid/backup/manager.py`, `tests/test_backup.py`

**Interfaces:**
```python
@dataclass
class BackupEntry: id: str; created: str; serial: str; model: str; codename: str; build_id: str
                   fingerprint: str; partition: str; slot: str; sha256: str; size: int; source: str; path: str
class BackupManager:
    def __init__(self, root: Path)
    def save(self, device: Device, partition: str, image: Path, source: str) -> BackupEntry  # copies to root/<serial>/<id>_<partition>.img, appends to root/<serial>/manifest.json
    def list(self, serial: str) -> list[BackupEntry]
    def latest(self, serial: str, partition: str, build_id: str | None = None) -> BackupEntry | None
    def has_backup(self, serial: str) -> bool
    def verify(self, entry: BackupEntry) -> bool  # sha256 match
```

### Task 5: Workflow engine and sessions

**Files:** `sudroid/workflow/__init__.py`, `sudroid/workflow/engine.py`, `sudroid/workflow/session.py`, `sudroid/ui/prompts.py`, `tests/test_engine.py`, `tests/test_prompts.py`

**Interfaces:**
```python
# prompts.py
def confirm(ctx: AppContext, question: str, *, default=False) -> bool   # ctx.yes -> True
def typed_confirm(ctx: AppContext, word: str, warning: str) -> None      # raises UserAbortError; NOT bypassed by --yes
def choose(ctx, prompt, options: list[str]) -> str

# session.py
@dataclass
class Session: id: str; serial: str; command: str; created: str; steps_done: list[str]; data: dict[str, str]; status: str
def new_session(serial, command) -> Session
def save(session) -> Path        # paths.sessions_dir()/<serial>/<id>.json
def latest_incomplete(serial, command) -> Session | None
def load(path) -> Session

# engine.py
class Step(ABC):
    name: str; title: str; mutating: bool = False
    def check(self, rt: Runtime) -> None      # raise PreconditionError to stop
    def run(self, rt: Runtime) -> None
    def undo(self, rt: Runtime) -> None       # default no-op
@dataclass
class Runtime: ctx: AppContext; device: Device; profile: VendorProfile; session: Session; work: Path; data: dict[str, str]
class Engine:
    def __init__(self, rt: Runtime, steps: list[Step])
    def plan_table(self) -> Table
    def run(self) -> None
        # for each step not in session.steps_done: check; if mutating and not ctx.yes: confirm; run; append to steps_done; save
        # on exception: log, mark session failed, offer undo of completed mutating steps in reverse (confirm), re-raise
```

### Task 6: Root steps and commands

**Files:** `sudroid/workflow/steps.py`, `sudroid/commands/root.py`, `sudroid/commands/backup.py`, `sudroid/commands/patch.py`, `sudroid/commands/flash.py`, `sudroid/commands/verify.py`, `sudroid/cli.py`, `tests/test_root_flow.py`, `tests/test_flash_cmd.py`

Steps (names are session keys):
- `check_tools`, `check_battery` (>= config.min_battery, PreconditionError), `check_unlocked` (LockState.UNLOCKED or PreconditionError hint `sudroid unlock`), `check_backend` (fastboot only in this phase; Samsung -> PreconditionError "phase 3")
- `acquire_image`: from `data["image"]` (path given by --image) else if device.root_present: `su -c dd if=/dev/block/by-name/<target><suffix>` to /data/local/tmp then pull; else PreconditionError with hint on obtaining stock image
- `backup_stock`: BackupManager.save(..., source)
- `fetch_magisk`: releases.fetch_release + download_apk + extract_bundle -> data["bundle_dir"], data["magisk_version"]
- `patch_image`: DevicePatcher -> data["patched"]
- `test_boot` (mutating, skipped when profile.supports_test_boot False or target is init_boot or --no-test-boot): adb reboot bootloader; fastboot.wait; fastboot boot patched; adb.wait_for_ready(240); root check `su -c id` contains `uid=0`; on failure PreconditionError "test boot did not yield root, nothing was written"; device stays booted on RAM image
- `flash_image` (mutating): if booted adb reboot bootloader; fastboot.wait; partition = profile.flash_partition(device, target); fastboot.flash; fastboot.reboot; undo: flash backup entry image
- `wait_boot`: adb.wait_for_ready(300)
- `install_app` (mutating): adb.install(apk)
- `verify_root`: `su -c id`, `su -c magisk -v`; store data["root"]

Commands:
- `root [--method magisk] [--image FILE] [--no-test-boot] [--skip-backup]`: build steps; `--dry-run` prints plan and executes read-only steps only (engine skips mutating steps when ctx.dry_run, printing the command it would run)
- `backup [--image FILE] [--partition boot|init_boot]`: register a stock image or pull from rooted device
- `patch IMAGE [--out FILE] [--magisk-version vX]`: device-side patch only, no flash
- `flash IMAGE [--partition ...] [--slot a|b|current] [--test-boot]`: inspect image, refuse if kind mismatch, confirm, flash
- `verify`: root presence table
- `restore [--partition]`: flash latest backup for build_id (basic version; full in phase 4)

Tests: FakeRunner scripted full happy path for pixel5 (boot target, test-boot on) asserting exact mutating call order; pixel7 (init_boot, test-boot skipped); low battery exit 20; locked exit 20; dry-run records no mutating calls in FakeRunner but engine prints plan; resume skips done steps; flash refuses non-boot image.

### Task 7: PR
Identity check, push, PR "v3 phase 2: root pipeline", CI green, merge.
