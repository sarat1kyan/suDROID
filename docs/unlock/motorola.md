# Motorola

Automated by the tool: yes.
Wipes data: yes.
Flash backend: fastboot.
Reference: https://en-us.support.motorola.com/app/standalone/bootloader/unlock-your-device-a

## Steps

1. Enable OEM unlocking and USB debugging in Developer options
2. Tool reboots to bootloader and runs: fastboot oem get_unlock_data
3. Paste the 5 lines (concatenated, no spaces) into the Motorola unlock page
4. Motorola emails a 20 character unlock key
5. Tool runs: fastboot oem unlock <KEY>. Device wipes.
