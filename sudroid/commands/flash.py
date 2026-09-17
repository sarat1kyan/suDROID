from __future__ import annotations

from pathlib import Path

from sudroid.context import AppContext, detect_device
from sudroid.device.model import FlashBackend
from sudroid.device.profiles import profile_for
from sudroid.errors import FlashError, PreconditionError
from sudroid.images.verify import inspect
from sudroid.paths import data_dir
from sudroid.ui import prompts
from sudroid.workflow import session as sm
from sudroid.workflow.engine import Engine, Runtime
from sudroid.workflow.steps import FlashImage, TestBoot, WaitBoot, _to_bootloader

KIND_FOR = {"boot": "boot", "init_boot": "boot", "vendor_boot": "vendor_boot", "vbmeta": "vbmeta"}


def run(
    ctx: AppContext,
    image: Path,
    *,
    partition: str | None = None,
    slot: str = "current",
    test_boot: bool = False,
) -> None:
    if not image.is_file():
        raise PreconditionError(f"image not found: {image}")
    device = detect_device(ctx)
    profile = profile_for(device)
    if profile.flash_backend is not FlashBackend.FASTBOOT:
        raise PreconditionError(
            f"{profile.name} needs {profile.flash_backend.value}",
            hint="Use `sudroid root --firmware AP.tar.md5` (Heimdall) or `--odin` for a tar.",
        )
    base = partition or profile.patch_target(device).value
    if base not in KIND_FOR:
        raise PreconditionError(f"unsupported partition {base}", hint=", ".join(KIND_FOR))
    info = inspect(image)
    if info.kind != KIND_FOR[base]:
        raise FlashError(
            f"{image.name} is a {info.kind} image, refusing to flash it to {base}",
            hint="Check you picked the right file.",
        )
    if base == "init_boot" and info.kernel_size:
        raise FlashError("image contains a kernel; init_boot images carry only a ramdisk")

    suffix = ""
    if device.ab:
        if slot == "current":
            suffix = device.slot_suffix
        elif slot in {"a", "b"}:
            suffix = f"_{slot}"
        else:
            raise PreconditionError("slot must be a, b or current")
    target_partition = f"{base}{suffix}"

    session = sm.new_session(device.serial, "flash")
    rt = Runtime(ctx, device, profile, session, data_dir() / "work" / session.id)
    rt.data["patched"] = str(image)
    rt.data["stock"] = str(image)
    if not test_boot or base != "boot":
        rt.data["no_test_boot"] = "1"

    class FlashGiven(FlashImage):
        def describe(self, rt: Runtime) -> str:
            return f"Flash {image.name} to {target_partition}"

        def run(self, rt: Runtime) -> None:
            fb = rt.ctx.fastboot()
            _to_bootloader(rt)
            if fb.getvar(f"partition-type:{target_partition}") is None and not rt.ctx.dry_run:
                raise FlashError(f"partition {target_partition} not present on device")
            r = fb.flash(target_partition, image)
            if not r.ok:
                raise FlashError(f"flash {target_partition} failed", hint=r.err)
            rt.data["flashed_partition"] = target_partition
            fb.reboot()

        def undo(self, rt: Runtime) -> None:
            return None

    ctx.console.print(
        f"{image.name}: {info.kind} header v{info.header_version}, {info.size} bytes, "
        f"sha256 {info.sha256[:16]}"
    )
    if not ctx.dry_run:
        prompts.require(ctx, f"Flash to {target_partition} on {device.model} ({device.serial})?")
    Engine(rt, [TestBoot(), FlashGiven(), WaitBoot()]).run()
    ctx.console.print(f"[green]flashed[/] {target_partition}")
