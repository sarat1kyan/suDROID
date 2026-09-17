# Sony Xperia

Automated by the tool: yes.
Wipes data: yes.
Flash backend: fastboot.
Reference: https://developer.sony.com/open-source/aosp-on-xperia-open-devices/get-started/unlock-bootloader

## Steps

1. Dial *#*#7378423#*#* > Service info > Configuration: confirm 'Bootloader unlock allowed: Yes'
2. Enable OEM unlocking and USB debugging
3. Get IMEI (Settings > About phone) and request the unlock code on the Sony developer site
4. Tool reboots to bootloader and runs: fastboot oem unlock 0x<CODE>. Device wipes.

## Notes

- Unlocking permanently erases Sony DRM keys (camera post-processing, some display features). This cannot be undone.
