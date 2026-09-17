# Google Pixel

Automated by the tool: yes.
Wipes data: yes.
Flash backend: fastboot.
Reference: https://source.android.com/docs/setup/build/running#unlocking-the-bootloader

## Steps

1. Settings > About phone > tap Build number 7 times
2. Settings > System > Developer options > enable OEM unlocking
3. Enable USB debugging, connect, accept the RSA prompt
4. Tool reboots to bootloader and runs: fastboot flashing unlock
5. Confirm on the phone with the volume keys, then power. Device wipes.

## Notes

- init_boot target: fastboot boot test-boot is not possible, the tool flashes directly after backup.
