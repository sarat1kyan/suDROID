# Support matrix

| Vendor | Unlock | Flash | Test boot | Stock image sources | Notes |
|---|---|---|---|---|---|
| Google Pixel | automated (`fastboot flashing unlock`) | fastboot | boot targets only | factory zip, OTA zip, `--auto-fetch` | Pixel 7 and later use init_boot |
| OnePlus | automated (`fastboot oem unlock`) | fastboot | yes | OTA zip (payload.bin) | OxygenOS 14+: use the full OTA |
| Motorola | automated with unlock key | fastboot | yes | firmware zip, `--image` | tool prints `get_unlock_data` |
| Sony Xperia | automated with unlock code | fastboot | yes | `--image` | unlock erases DRM keys |
| Nothing | automated | fastboot | yes | OTA zip | init_boot on newer models |
| ASUS | guided | fastboot | yes | firmware zip | unlock app discontinued for some models |
| Xiaomi / Redmi / POCO | guided (Mi Unlock, Windows) | fastboot | yes | fastboot ROM tgz (extract boot.img), `--image` | account binding wait |
| Samsung | guided (download mode) | Heimdall or Odin tar | no | AP tar (.tar.md5) | trips Knox permanently, US models cannot unlock |
| Generic fastboot | automated attempt | fastboot | yes | `--image` | MediaTek: mtkclient hint, Unisoc: token hint |

Root methods:

| Method | Automation | Target |
|---|---|---|
| Magisk | full: patch on device, test boot, flash, install manager | boot or init_boot |
| KernelSU | full on GKI kernels (android12-5.10 and newer): prebuilt boot image | boot |
| APatch | manager install and stock image staging, then `sudroid flash` | boot |

Host: Linux, macOS, Windows. Python 3.10 to 3.13 or the single file binary.
