# Troubleshooting

## `no device found`
- USB debugging on, cable supports data, phone unlocked and RSA prompt accepted.
- `sudroid doctor` checks the adb server, udev rules (Linux) and driver hints (Windows).
- Windows: install the Google USB Driver or the vendor driver, then unplug and replug.

## `device is unauthorized`
Accept the USB debugging prompt on the phone. Revoke and re-accept in Developer options if it does not appear.

## `bootloader state is locked`
Run `sudroid unlock`. Samsung and Xiaomi cannot be unlocked from the host; the tool prints the steps.

## `no stock image available`
Pass `--firmware` with the OTA zip, factory zip or Samsung AP tar for the installed build (`sudroid info` shows the build id), or `--image` with the extracted boot.img or init_boot.img. Pixel: `--auto-fetch`.

## `this is an incremental OTA`
Incremental payloads only carry diffs. Download the full OTA package or the factory image.

## `init_boot_a not present on device`
The partition table was not readable over adb and init_boot was inferred from the launch API level. Pass `--image` with the stock boot.img instead.

## Test boot fails or the phone hangs on the logo
Nothing was written. Hold Power for 10 seconds to reboot into the stock image. Try a different Magisk channel (`[magisk] channel = "canary"`) or set `keep_verity = false` in the config only if the device needs it.

## Bootloop after flashing
`sudroid restore` flashes the saved stock image back. If adb is unavailable, enter the bootloader manually (Volume Down + Power) and run `sudroid restore`.

## Samsung: Heimdall fails to detect
Use a USB 2.0 port, try another cable, remove Kies/Smart Switch drivers on Windows, or use `--odin` and flash the tar with Odin.

## `Failed to detect compatible download-mode device` after unlocking
First boot after unlock must complete setup with internet so VaultKeeper releases the bootloader; then retry.

## Logs
`~/.local/state/sudroid/sudroid.log` (Linux), `~/Library/Application Support/sudroid/` (macOS), `%LOCALAPPDATA%\sudroid\` (Windows). Session files with every step are under the data dir `sessions/<serial>/`.
