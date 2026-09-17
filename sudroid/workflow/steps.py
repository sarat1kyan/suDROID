"""Concrete workflow steps for root, flash and restore."""

from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path

import httpx

from sudroid.backup.manager import BackupManager
from sudroid.device.model import FlashBackend, PatchTarget
from sudroid.errors import FlashError, PreconditionError
from sudroid.images.verify import inspect
from sudroid.paths import cache_dir
from sudroid.root import releases
from sudroid.root.apk import MagiskBundle, extract_bundle
from sudroid.root.device_patch import DevicePatcher, PatchOptions
from sudroid.workflow.engine import Runtime, Step

log = logging.getLogger(__name__)

REMOTE_STOCK = "/data/local/tmp/sudroid_stock.img"


def _http_client() -> httpx.Client:
    return httpx.Client(headers={"User-Agent": "sudroid"})


def target_of(rt: Runtime) -> PatchTarget:
    return rt.profile.patch_target(rt.device)


def partition_of(rt: Runtime) -> str:
    return rt.profile.flash_partition(rt.device, target_of(rt))


class CheckTools(Step):
    name = "check_tools"
    title = "Check host tools"

    def run(self, rt: Runtime) -> None:
        rt.ctx.adb()
        if rt.profile.flash_backend is FlashBackend.FASTBOOT:
            rt.ctx.fastboot()


class CheckBackend(Step):
    name = "check_backend"
    title = "Check flash backend"

    def check(self, rt: Runtime) -> None:
        if rt.profile.flash_backend is not FlashBackend.FASTBOOT:
            raise PreconditionError(
                f"{rt.profile.name} uses {rt.profile.flash_backend.value}, "
                "which this command does not drive yet",
                hint="Samsung support (Heimdall, Odin tar) arrives in the next release.",
            )

    def run(self, rt: Runtime) -> None:
        return None


class CheckBattery(Step):
    name = "check_battery"
    title = "Check battery"

    def check(self, rt: Runtime) -> None:
        need = rt.ctx.config.general.min_battery
        have = rt.device.battery
        if have is None:
            log.warning("battery level unknown, continuing")
            return
        if have < need:
            raise PreconditionError(
                f"battery {have}% below minimum {need}%",
                hint="Charge the device or lower general.min_battery in config.",
            )

    def run(self, rt: Runtime) -> None:
        rt.say(f"battery {rt.device.battery}%")


class CheckUnlocked(Step):
    name = "check_unlocked"
    title = "Check bootloader unlocked"

    def check(self, rt: Runtime) -> None:
        if not rt.device.is_unlocked:
            raise PreconditionError(
                f"bootloader state is {rt.device.lock.value}",
                hint="Run `sudroid unlock` first. Unlocking wipes the device.",
            )

    def run(self, rt: Runtime) -> None:
        return None


class AcquireImage(Step):
    name = "acquire_image"
    title = "Acquire stock image"

    def describe(self, rt: Runtime) -> str:
        return f"Acquire stock {target_of(rt).value} image"

    def run(self, rt: Runtime) -> None:
        rt.work.mkdir(parents=True, exist_ok=True)
        dest = rt.work / f"stock_{target_of(rt).value}.img"
        given = rt.data.get("image")
        if given:
            src = Path(given).expanduser()
            if not src.is_file():
                raise PreconditionError(f"image not found: {src}")
            info = inspect(src)
            if not info.is_boot:
                raise PreconditionError(
                    f"{src.name} is not a boot image (kind={info.kind})",
                    hint="Provide the stock boot.img or init_boot.img for the installed build.",
                )
            shutil.copy2(src, dest)
            rt.data["stock_source"] = "user-file"
        elif rt.device.root_present:
            adb = rt.ctx.adb()
            part = partition_of(rt)
            rt.say(f"pulling /dev/block/by-name/{part} via existing root")
            r = adb.root_shell(f"dd if=/dev/block/by-name/{part} of={REMOTE_STOCK}", timeout=300)
            if not r.ok:
                raise PreconditionError("dd via su failed", hint=r.err)
            r = adb.pull(REMOTE_STOCK, dest)
            adb.root_shell(f"rm -f {REMOTE_STOCK}")
            if not r.ok or not dest.is_file():
                raise PreconditionError("pull of stock image failed", hint=r.err)
            rt.data["stock_source"] = "rooted-dd"
        else:
            raise PreconditionError(
                "no stock image available",
                hint=(
                    f"Pass --image <stock {target_of(rt).value}.img> extracted from the factory "
                    f"image or OTA for build {rt.device.build_id}. Firmware archive extraction "
                    "arrives in a later release."
                ),
            )
        rt.data["stock"] = str(dest)
        info = inspect(dest)
        rt.say(f"stock image: {dest.name} header v{info.header_version} {info.size} bytes")


class BackupStock(Step):
    name = "backup_stock"
    title = "Back up stock image"

    def skip(self, rt: Runtime) -> str:
        return "requested with --skip-backup" if rt.data.get("skip_backup") else ""

    def run(self, rt: Runtime) -> None:
        bm = BackupManager(rt.ctx.config.backup_dir)
        entry = bm.save(
            rt.device,
            target_of(rt).value,
            Path(rt.data["stock"]),
            rt.data.get("stock_source", "unknown"),
        )
        rt.data["backup_id"] = entry.id
        rt.data["backup_path"] = entry.path
        rt.say(f"backup: {entry.path}")


class FetchMagisk(Step):
    name = "fetch_magisk"
    title = "Fetch Magisk"

    def run(self, rt: Runtime) -> None:
        cfg = rt.ctx.config.magisk
        pinned = rt.data.get("magisk_version") or cfg.pinned_version
        with _http_client() as client:
            rel = releases.fetch_release(client, cfg.channel, pinned)
            apk = releases.download_apk(client, rel, cache_dir() / "magisk")
        abi = rt.device.abi or "arm64-v8a"
        bundle = extract_bundle(apk, abi, rt.work / "magisk", rel.version)
        rt.data["bundle_dir"] = str(bundle.dir)
        rt.data["bundle_files"] = ",".join(bundle.files)
        rt.data["magisk_version"] = rel.version
        rt.data["apk"] = str(apk)
        rt.say(f"Magisk {rel.version} ({rel.channel}) for {abi}")


def bundle_from(rt: Runtime) -> MagiskBundle:
    return MagiskBundle(
        Path(rt.data["bundle_dir"]),
        rt.data.get("magisk_version", ""),
        rt.device.abi,
        tuple(rt.data["bundle_files"].split(",")),
    )


class PatchImage(Step):
    name = "patch_image"
    title = "Patch image on device"
    mutating = True

    def skip(self, rt: Runtime) -> str:
        return "dry-run" if rt.ctx.dry_run else ""

    def run(self, rt: Runtime) -> None:
        cfg = rt.ctx.config.magisk
        opts = PatchOptions(
            keep_verity=cfg.keep_verity,
            keep_force_encrypt=cfg.keep_force_encrypt,
            patch_vbmeta=cfg.patch_vbmeta,
            recovery_mode=cfg.recovery_mode,
        )
        out = rt.work / f"patched_{target_of(rt).value}.img"
        res = DevicePatcher(rt.ctx.adb(), bundle_from(rt)).patch(Path(rt.data["stock"]), out, opts)
        rt.data["patched"] = str(res.image)
        rt.say(f"patched: {res.image.name} (Magisk {res.magisk_version})")


def _to_bootloader(rt: Runtime) -> None:
    adb = rt.ctx.adb()
    fb = rt.ctx.fastboot()
    if fb.devices():
        return
    if any(d.serial == rt.device.serial for d in adb.devices()):
        adb.reboot("bootloader")
    if not fb.wait(timeout=120):
        raise FlashError(
            "device did not appear in fastboot",
            hint="Hold Volume Down + Power to enter the bootloader manually, then retry.",
        )


class TestBoot(Step):
    name = "test_boot"
    title = "Test boot patched image (no write)"
    mutating = True

    def skip(self, rt: Runtime) -> str:
        if rt.data.get("no_test_boot"):
            return "disabled with --no-test-boot"
        if not rt.profile.supports_test_boot:
            return f"{rt.profile.name} does not support fastboot boot"
        if target_of(rt) is PatchTarget.INIT_BOOT:
            return "init_boot images cannot be test-booted"
        if rt.ctx.dry_run:
            return "dry-run"
        return ""

    def run(self, rt: Runtime) -> None:
        fb = rt.ctx.fastboot()
        adb = rt.ctx.adb()
        _to_bootloader(rt)
        r = fb.boot(Path(rt.data["patched"]))
        if not r.ok:
            raise FlashError("fastboot boot failed", hint=r.err)
        rt.say("booting from RAM, waiting for Android...")
        if not adb.wait_for_ready(240):
            raise PreconditionError(
                "device did not finish booting the test image; nothing was written",
                hint="Power cycle the phone to return to stock. The stock image may need a "
                "different Magisk version or options (keep_verity).",
            )
        r = adb.root_shell("id")
        if "uid=0" not in r.text:
            raise PreconditionError(
                "test boot completed but root is not available; nothing was written",
                hint=r.combined,
            )
        rt.data["test_boot"] = "ok"
        rt.say("test boot ok, root works")


class FlashImage(Step):
    name = "flash_image"
    title = "Flash patched image"
    mutating = True

    def describe(self, rt: Runtime) -> str:
        return f"Flash patched image to {partition_of(rt)}"

    def check(self, rt: Runtime) -> None:
        if not rt.data.get("patched"):
            raise PreconditionError("no patched image in session")

    def run(self, rt: Runtime) -> None:
        fb = rt.ctx.fastboot()
        _to_bootloader(rt)
        partition = partition_of(rt)
        if rt.device.ab:
            slot = fb.current_slot()
            if slot and slot != rt.device.slot:
                log.warning("fastboot reports slot %s, adb reported %s", slot, rt.device.slot)
                partition = f"{target_of(rt).value}_{slot}"
        if fb.getvar(f"partition-type:{partition}") is None and not rt.ctx.dry_run:
            if target_of(rt) is PatchTarget.INIT_BOOT:
                raise FlashError(
                    f"partition {partition} not present on device",
                    hint="init_boot was inferred but does not exist. Re-run `sudroid info` with a "
                    "readable partition table or pass --image with the stock boot.img.",
                )
            log.warning("cannot confirm partition %s via getvar, continuing", partition)
        r = fb.flash(partition, Path(rt.data["patched"]))
        if not r.ok:
            raise FlashError(f"flash {partition} failed", hint=r.err)
        rt.data["flashed_partition"] = partition
        rt.say(f"flashed {partition}")
        fb.reboot()

    def undo(self, rt: Runtime) -> None:
        backup = rt.data.get("backup_path") or rt.data.get("stock")
        partition = rt.data.get("flashed_partition")
        if not backup or not partition:
            return
        rt.say(f"restoring {partition} from {backup}")
        fb = rt.ctx.fastboot()
        _to_bootloader(rt)
        r = fb.flash(partition, Path(backup))
        if not r.ok:
            raise FlashError(f"restore of {partition} failed", hint=r.err)
        fb.reboot()


class WaitBoot(Step):
    name = "wait_boot"
    title = "Wait for Android"

    def skip(self, rt: Runtime) -> str:
        return "dry-run" if rt.ctx.dry_run else ""

    def run(self, rt: Runtime) -> None:
        if not rt.ctx.adb().wait_for_ready(300):
            log.warning("device did not report boot_completed within 5 minutes")


class InstallApp(Step):
    name = "install_app"
    title = "Install Magisk app"
    mutating = True

    def skip(self, rt: Runtime) -> str:
        return "" if rt.data.get("apk") else "no APK in session"

    def run(self, rt: Runtime) -> None:
        r = rt.ctx.adb().install(Path(rt.data["apk"]))
        if not r.ok:
            log.warning("APK install failed: %s", r.combined)
            rt.say("[yellow]install the Magisk app manually from the APK in the cache[/]")


class VerifyRoot(Step):
    name = "verify_root"
    title = "Verify root"

    def skip(self, rt: Runtime) -> str:
        return "dry-run" if rt.ctx.dry_run else ""

    def run(self, rt: Runtime) -> None:
        adb = rt.ctx.adb()
        ok = False
        for _ in range(5):
            r = adb.root_shell("id")
            if "uid=0" in r.text:
                ok = True
                break
            time.sleep(3)
        ver = adb.root_shell("magisk -v").text if ok else ""
        rt.data["root_verified"] = "yes" if ok else "no"
        rt.data["magisk_reported"] = ver
        if ok:
            rt.say(f"[green]root verified[/] magisk {ver}")
        else:
            rt.say(
                "[yellow]root not verified yet.[/] Open the Magisk app; it may ask for an "
                "additional setup reboot."
            )


def root_steps() -> list[Step]:
    return [
        CheckTools(),
        CheckBackend(),
        CheckBattery(),
        CheckUnlocked(),
        AcquireImage(),
        BackupStock(),
        FetchMagisk(),
        PatchImage(),
        TestBoot(),
        FlashImage(),
        WaitBoot(),
        InstallApp(),
        VerifyRoot(),
    ]
