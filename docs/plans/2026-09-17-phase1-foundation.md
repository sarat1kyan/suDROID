# Phase 1: Foundation Implementation Plan

**Goal:** Python package skeleton with tools layer, device detection, vendor profiles, and `info`/`doctor`/`profiles` commands, fully tested, CI green.

**Architecture:** `tools/` wraps subprocesses behind a `Runner` so tests inject fakes and `--dry-run` blocks writes. `device/detect.py` is a pure function from prop dumps to an immutable `Device`. Vendor logic lives only in `device/profiles/`. CLI is Typer with Rich rendering.

**Tech Stack:** Python 3.10+, typer, rich, platformdirs, httpx, tomli (py<3.11), pytest, ruff, mypy, hatchling, GitHub Actions.

**Spec:** `docs/specs/2026-09-17-sudroid-v3-design.md`

## Global Constraints

- Python 3.10 minimum, tested on 3.10 to 3.13.
- Only `sudroid/tools/` may call `subprocess`.
- No vendor branching outside `sudroid/device/profiles/`.
- Every device write goes through a `mutating=True` runner call.
- Plain ASCII in all files. No AI tool mentions. Short commit messages.
- Exit codes: 0 ok, 1 generic, 2 usage, 10 no device, 11 multiple devices, 12 tool missing, 20 precondition failed, 30 user aborted, 40 patch failed, 50 flash failed.

---

### Task 1: Project skeleton and tooling

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `.pre-commit-config.yaml`, `sudroid/__init__.py`, `sudroid/__main__.py`, `sudroid/errors.py`, `tests/__init__.py`, `tests/test_version.py`, `.github/workflows/ci.yml`

**Interfaces:**
- Produces: `sudroid.__version__ = "3.0.0a1"`, `sudroid.errors.SudroidError(message, exit_code)` and subclasses `NoDeviceError(10)`, `MultipleDevicesError(11)`, `ToolMissingError(12)`, `PreconditionError(20)`, `UserAbortError(30)`, `PatchError(40)`, `FlashError(50)`.

Steps:
- [ ] Write `tests/test_version.py` asserting `sudroid.__version__` matches `^\d+\.\d+\.\d+`.
- [ ] `pyproject.toml`: hatchling, deps typer>=0.12, rich>=13, platformdirs>=4, httpx>=0.27, tomli>=2 for py<3.11; optional `dev` extra: pytest, pytest-cov, ruff, mypy. Script `sudroid = "sudroid.cli:app"`. ruff: line-length 100, select E,F,I,UP,B,SIM. mypy strict.
- [ ] `errors.py` with hierarchy above.
- [ ] `.github/workflows/ci.yml`: matrix os x python, `pip install -e .[dev]`, `ruff check`, `ruff format --check`, `mypy sudroid`, `pytest`.
- [ ] Run `pytest`, `ruff`, `mypy`. Commit `Add package skeleton and CI`.

### Task 2: Runner and Result

**Files:**
- Create: `sudroid/tools/__init__.py`, `sudroid/tools/base.py`, `tests/test_runner.py`

**Interfaces:**
```python
@dataclass(frozen=True)
class Result:
    args: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    duration: float
    @property
    def ok(self) -> bool
    @property
    def text(self) -> str  # stdout stripped, CRLF normalized

class Runner(Protocol):
    def run(self, args: Sequence[str], *, timeout: float = 60, mutating: bool = False,
            input: bytes | None = None) -> Result

class SubprocessRunner: real subprocess, logs each call at DEBUG
class DryRunRunner(inner: Runner): non-mutating -> inner; mutating -> record in .recorded, return Result ok
class FakeRunner: tests; responses dict keyed by tuple(args) or callable; .calls list
```

Steps:
- [ ] Tests: SubprocessRunner runs `python -c print(1)` and returns ok with stdout `1`; DryRunRunner passes read-through and records mutating; FakeRunner returns programmed response and raises `KeyError` for unknown args with clear message.
- [ ] Implement. Commit `Add subprocess runner with dry-run and fake`.

### Task 3: Props parser

**Files:**
- Create: `sudroid/device/__init__.py`, `sudroid/device/props.py`, `tests/test_props.py`, `tests/fixtures/getprop/pixel7.txt`, `pixel5.txt`, `oneplus9.txt`, `s23.txt`, `mi11.txt`, `motog.txt`, `xperia5.txt`, `generic_mtk.txt`

**Interfaces:**
```python
class Props(Mapping[str, str]):
    @classmethod
    def parse(cls, text: str) -> Props   # lines like "[ro.x]: [value]"
    def get(self, key, default="") -> str
    def get_int(self, key, default=None) -> int | None
    def first(self, *keys) -> str        # first non-empty
```

Steps:
- [ ] Fixtures: realistic getprop dumps (30 to 60 lines each) with the fields listed in spec section 5.
- [ ] Tests: parse handles CRLF, empty values, values containing `]: [`; `first` order.
- [ ] Implement. Commit `Add getprop parser and device fixtures`.

### Task 4: Device model and detection

**Files:**
- Create: `sudroid/device/model.py`, `sudroid/device/detect.py`, `tests/test_detect.py`

**Interfaces:**
```python
class Vendor(str, Enum): GOOGLE, SAMSUNG, XIAOMI, ONEPLUS, MOTOROLA, SONY, ASUS, NOTHING, GENERIC
class SocVendor(str, Enum): QUALCOMM, MEDIATEK, EXYNOS, TENSOR, UNISOC, UNKNOWN
class LockState(str, Enum): LOCKED, UNLOCKED, UNKNOWN
class PatchTarget(str, Enum): BOOT, INIT_BOOT
class FlashBackend(str, Enum): FASTBOOT, HEIMDALL, ODIN_TAR

@dataclass(frozen=True)
class Device:
    serial, model, brand, manufacturer, codename: str
    android: str; sdk: int; first_api_level: int; build_id: str; fingerprint: str; security_patch: str
    vendor: Vendor; soc: SocVendor; soc_model: str
    ab: bool; slot: str            # "a", "b" or ""
    has_init_boot: bool; has_vendor_boot: bool; dynamic_partitions: bool
    patch_target: PatchTarget
    lock: LockState; oem_unlock_allowed: bool | None
    encryption: str
    root_present: str              # "", "magisk", "kernelsu", "apatch", "su"
    battery: int | None

@dataclass(frozen=True)
class RawInfo:
    props: Props
    byname: frozenset[str] = frozenset()
    fastboot_vars: Mapping[str, str] = {}
    which: Mapping[str, bool] = {}   # su, magisk, ksud, apd presence
    battery: int | None = None

def detect(raw: RawInfo) -> Device
```

Rules (encode exactly):
- vendor: manufacturer lowercased in {google, samsung, xiaomi, oneplus, motorola, sony, asus, nothing}; brand fallback {redmi, poco -> XIAOMI; motorola/moto -> MOTOROLA}; else GENERIC.
- soc: ro.soc.manufacturer / ro.hardware / ro.board.platform contains qcom|qualcomm|msm|sm -> QUALCOMM; mt -> MEDIATEK; exynos|s5e -> EXYNOS; tensor|gs101|gs201|zuma -> TENSOR; unisoc|sprd|ums -> UNISOC.
- ab: slot_suffix non-empty or ro.build.ab_update=true or fastboot slot-count > 1.
- has_init_boot: "init_boot" or "init_boot_a" in byname, or fastboot `has-slot:init_boot` == yes, or first_api_level >= 33.
- patch_target: INIT_BOOT if has_init_boot else BOOT.
- lock: fastboot unlocked yes/no wins; else verifiedbootstate orange -> UNLOCKED, green -> LOCKED; else flash.locked 0/1; else vbmeta.device_state; else UNKNOWN.
- root_present: magisk > ksud > apd > su by which map.

Steps:
- [ ] Tests per fixture: pixel7 -> GOOGLE, TENSOR, INIT_BOOT, ab; pixel5 -> BOOT; s23 -> SAMSUNG, QUALCOMM, no slot; mi11 -> XIAOMI; motog -> MOTOROLA; xperia5 -> SONY; generic_mtk -> GENERIC + MEDIATEK; lock precedence tests.
- [ ] Implement. Commit `Add device model and detection`.

### Task 5: Vendor profiles

**Files:**
- Create: `sudroid/device/profiles/__init__.py`, `base.py`, `google.py`, `samsung.py`, `xiaomi.py`, `oneplus.py`, `motorola.py`, `sony.py`, `asus.py`, `nothing.py`, `generic.py`, `registry.py`, `tests/test_profiles.py`

**Interfaces:**
```python
@dataclass(frozen=True)
class Quirk:
    code: str
    message: str

class VendorProfile(ABC):
    name: str
    vendor: Vendor
    flash_backend: FlashBackend
    supports_test_boot: bool = True
    def unlock_steps(self, d: Device) -> list[str]
    def unlock_commands(self, d: Device) -> list[list[str]]   # fastboot arg lists tried in order; [] when not automatable
    def needs_unlock_data(self, d: Device) -> bool             # Motorola/Sony: tool must fetch data first
    def patch_target(self, d: Device) -> PatchTarget          # default d.patch_target
    def quirks(self, d: Device) -> list[Quirk]

def profile_for(d: Device) -> VendorProfile
def all_profiles() -> list[VendorProfile]
```
Content per spec section 6 table. Generic profile adds MediaTek (mtkclient) and Unisoc quirks by soc. Samsung: flash_backend HEIMDALL, supports_test_boot False, quirks for KG/RMM (`ro.boot.other.locked`, `ro.boot.warranty_bit`) and OEM toggle.

Steps:
- [ ] Tests: registry maps each fixture device to right profile; Samsung has no unlock_commands; Motorola needs_unlock_data; Google Pixel 7 patch_target INIT_BOOT; generic MTK emits mtkclient quirk; no profile text contains "http://" short links (assert only https and allowed hosts).
- [ ] Implement. Commit `Add vendor profiles`.

### Task 6: adb and fastboot clients

**Files:**
- Create: `sudroid/tools/adb.py`, `sudroid/tools/fastboot.py`, `tests/test_adb.py`, `tests/test_fastboot.py`

**Interfaces:**
```python
@dataclass(frozen=True)
class AdbDevice: serial: str; state: str   # device, unauthorized, offline, recovery, sideload

class AdbClient:
    def __init__(self, runner: Runner, path: str = "adb", serial: str | None = None)
    def devices(self) -> list[AdbDevice]
    def shell(self, cmd: str, *, timeout=60) -> Result
    def getprop_all(self) -> Props
    def getprop(self, key: str) -> str
    def list_byname(self) -> frozenset[str]        # ls /dev/block/by-name, empty on failure
    def which(self, name: str) -> bool
    def battery_level(self) -> int | None
    def pull(self, remote: str, local: Path) -> Result      # mutating=False
    def push(self, local: Path, remote: str) -> Result      # mutating=True
    def install(self, apk: Path) -> Result                  # mutating=True
    def reboot(self, target: str = "") -> Result            # mutating=True; "", "bootloader", "recovery", "download"
    def wait_for_device(self, timeout=180) -> Result
    def root_shell(self, cmd: str) -> Result                # su -c

class FastbootClient:
    def __init__(self, runner, path="fastboot", serial=None)
    def devices(self) -> list[str]
    def getvar(self, name: str) -> str | None
    def getvar_all(self) -> dict[str, str]
    def current_slot(self) -> str
    def has_slot(self, partition: str) -> bool
    def unlocked(self) -> bool | None
    def flash(self, partition: str, image: Path) -> Result  # mutating
    def boot(self, image: Path) -> Result                   # mutating
    def reboot(self, target: str = "") -> Result            # mutating
    def oem(self, *args: str) -> Result                     # mutating
    def flashing(self, *args: str) -> Result                # mutating
    def wait(self, timeout=180) -> None                     # poll devices()
```
fastboot getvar output arrives on stderr as `name: value` and ends with `Finished.`. Parse both streams.

Steps:
- [ ] Tests with FakeRunner: devices parsing incl. unauthorized; getprop_all uses `getprop` dump; getvar_all parses stderr, drops `Finished`, handles `(bootloader)` prefix; `--serial` injected as `-s`; flash marked mutating (DryRunRunner records it).
- [ ] Implement. Commit `Add adb and fastboot clients`.

### Task 7: Platform tools locator and downloader

**Files:**
- Create: `sudroid/tools/platform_tools.py`, `sudroid/paths.py`, `tests/test_platform_tools.py`

**Interfaces:**
```python
# paths.py
def cache_dir() -> Path; def config_dir() -> Path; def state_dir() -> Path; def data_dir() -> Path  # platformdirs, app "sudroid"

# platform_tools.py
PLATFORM_TOOLS_URL = {"linux": ".../platform-tools-latest-linux.zip", "darwin": "...-darwin.zip", "windows": "...-windows.zip"}
def locate(name: str, override: str = "", extra_dirs: Sequence[Path] = ()) -> Path | None
def ensure(name: str, *, override="", auto_download=True, client: httpx.Client | None = None) -> Path   # raises ToolMissingError
def download_platform_tools(client, dest: Path) -> Path   # returns dir containing adb
def version(path: Path) -> str
```
`locate` order: override, PATH, `cache_dir()/platform-tools`, common dirs (`~/Android/Sdk/platform-tools`, `%LOCALAPPDATA%/Android/Sdk/platform-tools`, `/opt/homebrew/bin`).

Steps:
- [ ] Tests: locate finds override; finds in fake PATH via monkeypatch; ensure raises ToolMissingError when auto_download False; download uses httpx MockTransport serving a tiny zip containing `platform-tools/adb` and extracts with exec bit on posix.
- [ ] Implement. Commit `Add platform-tools locator and downloader`.

### Task 8: Config and logging

**Files:**
- Create: `sudroid/config.py`, `sudroid/log.py`, `tests/test_config.py`, `tests/test_log.py`

**Interfaces:**
```python
@dataclass
class GeneralConfig: min_battery: int = 50; backup_dir: str = "~/sudroid-backups"; log_level: str = "info"
@dataclass
class MagiskConfig: channel="stable"; pinned_version=""; keep_verity=True; keep_force_encrypt=True; patch_vbmeta=False; recovery_mode=False
@dataclass
class ToolsConfig: adb=""; fastboot=""; heimdall=""; auto_download=True
@dataclass
class Config: general; magisk; tools
def load(path: Path | None = None, env: Mapping[str,str] = os.environ) -> Config   # defaults < toml < SUDROID_* env
def default_path() -> Path

# log.py
def setup(level: str, *, json_mode: bool, log_file: Path | None) -> Console   # returns rich Console (stderr when json_mode)
def get_logger(name) -> logging.Logger
```
Env mapping: `SUDROID_GENERAL_MIN_BATTERY=40`, `SUDROID_TOOLS_ADB=/x/adb`.

Steps:
- [ ] Tests: defaults; toml override; env override wins; unknown keys ignored with warning; json_mode routes console to stderr; file handler created.
- [ ] Implement. Commit `Add config loading and logging`.

### Task 9: CLI with doctor, info, profiles

**Files:**
- Create: `sudroid/cli.py`, `sudroid/context.py`, `sudroid/ui/__init__.py`, `sudroid/ui/render.py`, `sudroid/commands/__init__.py`, `sudroid/commands/doctor.py`, `sudroid/commands/info.py`, `sudroid/commands/profiles.py`, `tests/test_cli.py`

**Interfaces:**
```python
@dataclass
class AppContext:
    config: Config; console: Console; runner: Runner; dry_run: bool; json: bool; serial: str | None
    def adb(self) -> AdbClient        # ensure() tool, cached
    def fastboot(self) -> FastbootClient

def gather(ctx: AppContext) -> RawInfo    # adb getprop, byname, which, battery; fastboot vars only if in bootloader
def pick_device(adb: AdbClient, serial: str | None) -> AdbDevice   # raises NoDeviceError / MultipleDevicesError

# render.py
def device_table(d: Device, profile: VendorProfile) -> Table
def support_matrix(profiles: list[VendorProfile]) -> Table
def doctor_table(rows: list[tuple[str, str, str]]) -> Table   # name, status, detail
```
`cli.py`: Typer app, global callback builds `AppContext`, `SudroidError` mapped to exit codes, `--json` prints `dataclasses.asdict(device)`.
`doctor`: rows for adb, fastboot, heimdall, python, OS, adb server (`adb start-server` non-mutating), udev rule presence on Linux (`/etc/udev/rules.d/*android*`), Windows driver hint text.

Steps:
- [ ] Tests with Typer CliRunner and FakeRunner injected via env hook `SUDROID_TEST_RUNNER` fixture: `profiles` prints all 9 names; `info --json` on pixel7 fixture outputs vendor google and patch_target init_boot; `info` with zero devices exits 10; two devices without `--serial` exits 11; `doctor` exits 0 with fake tools present, exits 12 when adb missing and auto_download false.
- [ ] Implement. Commit `Add cli with doctor, info and profiles`.

### Task 10: Legacy move and phase 1 docs

**Files:**
- Move: `suDROID - v2.0.ps1`, `suDROID - v2.0.sh`, `suDROID2.1.sh` -> `legacy/` with header comment `Deprecated. Superseded by the sudroid Python CLI. Removed in v3.1.`
- Create: `legacy/README.md`, `CHANGELOG.md` (Unreleased section), `CONTRIBUTING.md`, `SECURITY.md`

Steps:
- [ ] `git mv`, add headers, docs. Run full `pytest`, `ruff`, `mypy`. Commit `Move v2 scripts to legacy and add project docs`.

### Task 11: PR

- [ ] Verify identity (name, email, gh account). Push `v3` with `-u`. Open PR "v3 phase 1: package skeleton, detection, cli" with short body listing commands added. Wait CI. Merge with squash off (keep commits) via `gh pr merge --merge`. Delete branch.
