# Phase 4: Firmware Sources and Root Methods Implementation Plan

**Goal:** `--firmware` accepts OTA zips (payload.bin), Pixel factory zips and raw payload files for fastboot devices. Pixel builds can be fetched automatically. `--method kernelsu` flashes a matching GKI prebuilt; `--method apatch` installs the manager and hands off to `sudroid flash`.

**Architecture:** A minimal protobuf wire decoder reads `DeltaArchiveManifest` from payload.bin so only the needed partitions (boot, init_boot, vbmeta) are extracted from full OTAs. `images/sources.py` dispatches by archive shape. Pixel factory URLs come from the Google factory images page, verified against the listed sha256. KernelSU GKI assets are matched by the device kernel KMI string.

**Spec:** `docs/specs/2026-09-17-sudroid-v3-design.md` section 9.

---

### Task 1: payload.bin reader

**Files:** `sudroid/images/payload.py`, `tests/test_payload.py`

```python
class PayloadError(PreconditionError)
@dataclass class Extent: start_block: int; num_blocks: int
@dataclass class Operation: type: int; data_offset: int; data_length: int; dst_extents: list[Extent]; sha256: bytes
@dataclass class Partition: name: str; ops: list[Operation]; size: int; hash: bytes
@dataclass class Payload: block_size: int; partitions: dict[str, Partition]; data_offset: int; source: BinaryIO
def open_payload(fh: BinaryIO) -> Payload          # magic CrAU, version 2, manifest, metadata sig size
def extract(payload: Payload, name: str, out: Path) -> Path   # REPLACE, REPLACE_BZ, REPLACE_XZ, ZERO; others -> PayloadError "incremental OTA"
def extract_from_zip(zip_path: Path, names, dest) -> dict[str, Path]   # payload.bin entry, must be stored
```
Protobuf: tag varint, wire types 0 (varint), 2 (length delimited), 1 (fixed64), 5 (fixed32). Field numbers: manifest.block_size=3, partitions=13; PartitionUpdate.partition_name=1, operations=8, new_partition_info=7; InstallOperation.type=1, data_offset=2, data_length=3, dst_extents=6, data_sha256_hash=8; Extent.start_block=1, num_blocks=2; PartitionInfo.size=1, hash=2. Op types: REPLACE=0, REPLACE_BZ=1, ZERO=6, REPLACE_XZ=8.
Tests: a tiny protobuf encoder in the test builds a payload with boot (REPLACE + ZERO) and vbmeta (REPLACE_XZ), verifies bytes and sha256; incremental op type raises; zip wrapper works.

### Task 2: factory zip and dispatcher

**Files:** `sudroid/images/factory.py`, `sudroid/images/sources.py`, `tests/test_sources.py`

```python
# factory.py
def extract_factory(zip_path, names, dest) -> dict[str, Path]   # nested image-*.zip or top level *.img
# sources.py
def extract_firmware(archive: Path, names: Iterable[str], dest: Path) -> dict[str, Path]
    # .tar/.tar.md5 -> samsung.extract_ap; .bin -> payload; .zip: payload.bin inside -> payload, image-*.zip inside -> factory, *.img inside -> direct; .img -> copy
```
`AcquireImage` uses `extract_firmware` for all vendors and stores `vbmeta` when present.

### Task 3: Pixel factory auto fetch

**Files:** `sudroid/images/pixel_factory.py`, `tests/test_pixel_factory.py`, `sudroid/workflow/steps.py` (AcquireImage: `--auto-fetch`)

```python
FACTORY_PAGE = "https://developers.google.com/android/images"
@dataclass class FactoryImage: codename: str; build_id: str; url: str; sha256: str
def find_factory_image(html: str, codename: str, build_id: str) -> FactoryImage | None
    # link pattern: dl.google.com/dl/android/aosp/<codename>-<build lower>-factory-<8hex>.zip ; sha256 is the 64-hex in the same table row
def download_factory(client, image, cache) -> Path      # streaming, sha256 verified, .sha256 sidecar
```
Flow: Google vendor, no --image/--firmware, `--auto-fetch` given or prompt "download factory image for <build> from Google (about 2.5 GB)?" Requires accepting Google terms: print the page URL and require confirm.

### Task 4: APatch and KernelSU

**Files:** `sudroid/root/github.py`, `sudroid/root/apatch.py`, `sudroid/root/kernelsu.py`, `sudroid/workflow/steps.py`, `sudroid/commands/root.py`, `tests/test_methods.py`

```python
# github.py
@dataclass class Release: tag: str; assets: dict[str, str]   # name -> url
def latest_release(client, repo: str) -> Release   # api.github.com/repos/<repo>/releases/latest
# apatch.py
REPO = "bmax121/APatch"; def manager_apk(rel) -> str|None
# kernelsu.py
REPO = "tiann/KernelSU"; def kmi_of(kernel_release: str) -> str|None  # "5.10.209-android12-9-..." -> "android12-5.10"
def match_boot_asset(rel, kmi) -> str|None  # name contains f"{kmi}" ... "-boot.img.gz", prefer plain (no -lz4)
```
Device gains `kernel: str` from `adb shell uname -r`.
root --method kernelsu: GKI check (kmi found and sdk >= 31) else PreconditionError with guide; download asset, gunzip, `TestBoot` then `FlashImage` on boot; install manager APK; verify via `ksud`.
root --method apatch: install manager APK from release, print steps (patch in app with superkey, copy out, run `sudroid flash <img>`).

### Task 5: PR
