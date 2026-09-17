"""Concrete workflow steps for root, flash and restore."""

from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path

import httpx

from sudroid.backup.manager import BackupManager
from sudroid.device.model import FlashBackend, PatchTarget, Vendor
from sudroid.device.profiles.base import VendorProfile
from sudroid.errors import FlashError, PreconditionError
from sudroid.images import pixel_factory
from sudroid.images.sources import extract_firmware
from sudroid.images.verify import inspect
from sudroid.paths import cache_dir
from sudroid.root import apatch, kernelsu, releases
from sudroid.root.apk import MagiskBundle, extract_bundle
from sudroid.root.device_patch import DevicePatcher, PatchOptions
from sudroid.root.github import download_asset, latest_release
from sudroid.ui import prompts
from sudroid.workflow.engine import Runtime, Step

log = logging.getLogger(__name__)

REMOTE_STOCK = "/data/local/tmp/sudroid_stock.img"


def _http_client() -> httpx.Client:
    return httpx.Client(headers={"User-Agent": "sudroid"})


def target_of(rt: Runtime) -> PatchTarget:
    override = rt.data.get("target")
    if override:
        return PatchTarget(override)
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

    def skip(self, rt: Runtime) -> str:
        if rt.data.get("skip_backup") and rt.data.get("method", "magisk") != "magisk":
            return "no stock image needed without backup"
        return ""

    def run(self, rt: Runtime) -> None:
        rt.work.mkdir(parents=True, exist_ok=True)
        dest = rt.work / f"stock_{target_of(rt).value}.img"
        given = rt.data.get("image")
        firmware = rt.data.get("firmware")
        if not given and not firmware and rt.data.get("auto_fetch"):
            firmware = self._auto_fetch(rt)
        if firmware and not given:
            fw = Path(firmware).expanduser()
            want = f"{target_of(rt).value}.img"
            found = extract_firmware(fw, (want, "vbmeta.img"), rt.work / "firmware")
            if want not in found:
                raise PreconditionError(
                    f"{want} not found in {fw.name}",
                    hint=f"Archive contains: {', '.join(sorted(found))}. "
                    "Use the firmware package for the installed build.",
                )
            shutil.copy2(found[want], dest)
            if "vbmeta.img" in found:
                rt.data["vbmeta"] = str(found["vbmeta.img"])
            rt.data["stock_source"] = f"firmware:{fw.name}"
            given = ""
        elif given:
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

    def _auto_fetch(self, rt: Runtime) -> str:
        d = rt.device
        if d.vendor is not Vendor.GOOGLE:
            raise PreconditionError(
                "automatic firmware download is only available for Google Pixel",
                hint="Pass --firmware with the OTA or factory package for your build.",
            )
        rt.say(f"looking up factory image for {d.codename} {d.build_id}")
        rt.say(f"source: {pixel_factory.FACTORY_PAGE}")
        rt.say(
            "Downloading means you accept Google's terms shown on that page. "
            "The archive is about 2 to 3 GB."
        )
        if not rt.ctx.dry_run:
            prompts.require(rt.ctx, "Download the factory image?")
        with _http_client() as client:
            html = pixel_factory.fetch_page(client)
            image = pixel_factory.find_image(html, d.codename, d.build_id)
            if image is None:
                builds = pixel_factory.list_builds(html, d.codename)
                raise PreconditionError(
                    f"no factory image listed for {d.codename} build {d.build_id}",
                    hint=f"listed builds: {', '.join(builds[-5:]) or 'none'}. Use --firmware.",
                )
            path = pixel_factory.download(client, image, cache_dir() / "factory")
        return str(path)


class BackupStock(Step):
    name = "backup_stock"
    title = "Back up stock image"

    def skip(self, rt: Runtime) -> str:
        if rt.data.get("skip_backup"):
            return "requested with --skip-backup"
        return "" if rt.data.get("stock") else "no stock image acquired"

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
        vb = rt.data.get("vbmeta")
        if vb:
            vb_entry = bm.save(
                rt.device, "vbmeta", Path(vb), rt.data.get("stock_source", "unknown")
            )
            rt.data["backup_vbmeta_path"] = vb_entry.path


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
    booted = [d for d in adb.devices() if d.ready]
    if any(adb.serial is None or d.serial == adb.serial for d in booted):
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

    def skip(self, rt: Runtime) -> str:
        if rt.ctx.dry_run and not rt.data.get("patched"):
            return "dry-run, no patched image"
        return ""

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


class FetchKernelSU(Step):
    name = "fetch_kernelsu"
    title = "Fetch KernelSU GKI kernel"

    def check(self, rt: Runtime) -> None:
        if rt.profile.flash_backend is not FlashBackend.FASTBOOT:
            raise PreconditionError(
                "KernelSU automated flow needs fastboot",
                hint="Patch with the KernelSU app or flash a KernelSU boot image manually.",
            )
        if kernelsu.kmi_of(rt.device.kernel) is None:
            raise PreconditionError(
                f"kernel {rt.device.kernel or 'unknown'} is not a GKI kernel",
                hint="\n".join(kernelsu.steps_manual()),
            )

    def run(self, rt: Runtime) -> None:
        kmi = kernelsu.kmi_of(rt.device.kernel) or ""
        with _http_client() as client:
            rel = latest_release(client, kernelsu.REPO, cache_dir() / "github")
            match = kernelsu.match_boot_asset(rel, kmi)
            if match is None:
                raise PreconditionError(
                    f"KernelSU {rel.tag} has no prebuilt for KMI {kmi}",
                    hint="\n".join(kernelsu.steps_manual()),
                )
            name, url = match
            rt.say(f"KernelSU {rel.tag}: {name}")
            gz = download_asset(client, url, cache_dir() / "kernelsu" / rel.tag / name)
            manager = kernelsu.manager_apk(rel)
            if manager:
                apk_name, apk_url = manager
                apk = download_asset(client, apk_url, cache_dir() / "kernelsu" / rel.tag / apk_name)
                rt.data["apk"] = str(apk)
        rt.work.mkdir(parents=True, exist_ok=True)
        img = kernelsu.gunzip(gz, rt.work / "kernelsu_boot.img")
        info = inspect(img)
        if not info.is_boot:
            raise PreconditionError(f"{name} did not unpack to a boot image")
        rt.data["patched"] = str(img)
        rt.data["target"] = PatchTarget.BOOT.value
        rt.data["magisk_version"] = f"KernelSU {rel.tag}"


class FetchAPatch(Step):
    name = "fetch_apatch"
    title = "Install APatch manager and stage stock image"
    mutating = True

    def run(self, rt: Runtime) -> None:
        with _http_client() as client:
            rel = latest_release(client, apatch.REPO, cache_dir() / "github")
            manager = apatch.manager_apk(rel)
            if not manager:
                raise PreconditionError(f"APatch {rel.tag} has no manager APK asset")
            apk_name, apk_url = manager
            apk = download_asset(client, apk_url, cache_dir() / "apatch" / rel.tag / apk_name)
        rt.data["apk"] = str(apk)
        adb = rt.ctx.adb()
        r = adb.install(apk)
        if not r.ok:
            log.warning("APatch install failed: %s", r.combined)
        stock = rt.data.get("stock")
        if stock:
            adb.push(Path(stock), f"/sdcard/Download/stock_{target_of(rt).value}.img")
            rt.say(f"stock image copied to Download/stock_{target_of(rt).value}.img")
        rt.say(f"[bold]APatch {rel.tag} installed. Next steps:[/]")
        for i, line in enumerate(apatch.steps(), 1):
            rt.say(f"  {i}. {line}")


class SkipInOdinMode(Step):
    """Mixin-like base: steps that cannot run when the user flashes with Odin."""

    def skip(self, rt: Runtime) -> str:
        if rt.data.get("odin"):
            return "flash with Odin first, then run sudroid verify"
        return super().skip(rt)

    def run(self, rt: Runtime) -> None:  # pragma: no cover - overridden
        raise NotImplementedError


class WaitBootAfterOdin(SkipInOdinMode, WaitBoot):
    def run(self, rt: Runtime) -> None:
        WaitBoot.run(self, rt)


class InstallAppAfterOdin(SkipInOdinMode, InstallApp):
    def run(self, rt: Runtime) -> None:
        InstallApp.run(self, rt)


class VerifyRootAfterOdin(SkipInOdinMode, VerifyRoot):
    def run(self, rt: Runtime) -> None:
        VerifyRoot.run(self, rt)


def root_steps(profile: VendorProfile, method: str = "magisk") -> list[Step]:
    if method == "kernelsu":
        return [
            CheckTools(),
            CheckBattery(),
            CheckUnlocked(),
            AcquireImage(),
            BackupStock(),
            FetchKernelSU(),
            TestBoot(),
            FlashImage(),
            WaitBoot(),
            InstallApp(),
            VerifyRoot(),
        ]
    if method == "apatch":
        return [
            CheckTools(),
            CheckBattery(),
            CheckUnlocked(),
            AcquireImage(),
            BackupStock(),
            FetchAPatch(),
        ]
    if method != "magisk":
        raise PreconditionError(f"unknown method {method}", hint="magisk, kernelsu or apatch")
    if profile.flash_backend is FlashBackend.FASTBOOT:
        return [
            CheckTools(),
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
    from sudroid.workflow.samsung_steps import (
        CheckHeimdall,
        EnterDownloadMode,
        HeimdallFlash,
        OdinTarOut,
        PatchVbmeta,
    )

    return [
        CheckTools(),
        CheckHeimdall(),
        CheckBattery(),
        CheckUnlocked(),
        AcquireImage(),
        BackupStock(),
        FetchMagisk(),
        PatchImage(),
        PatchVbmeta(),
        OdinTarOut(),
        EnterDownloadMode(),
        HeimdallFlash(),
        WaitBootAfterOdin(),
        InstallAppAfterOdin(),
        VerifyRootAfterOdin(),
    ]
