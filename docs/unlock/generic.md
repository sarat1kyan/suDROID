# Generic fastboot

Automated by the tool: yes.
Wipes data: yes.
Flash backend: fastboot.

## Steps

1. Enable OEM unlocking and USB debugging
2. Tool reboots to bootloader and tries: fastboot flashing unlock, then fastboot oem unlock
3. If both fail the vendor needs a token or tool. See quirks for chipset hints.

## Notes

- MediaTek SoC. If the vendor offers no unlock path, mtkclient (https://github.com/bkerler/mtkclient) can unlock via BROM on many models.
