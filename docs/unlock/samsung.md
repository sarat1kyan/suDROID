# Samsung Galaxy

Automated by the tool: no, guided.
Wipes data: yes.
Flash backend: heimdall.

## Steps

1. Developer options > enable OEM unlocking (if missing: set date back 7 days, toggle auto date off, or wait 7 days on fresh firmware, RMM/KG prenormal lock)
2. Power off. Hold Volume Up + Volume Down and plug in USB to enter download mode
3. Long press Volume Up on the warning screen to open the unlock menu
4. Press Volume Up to unlock. Device wipes and reboots
5. Complete setup, connect to WiFi, then confirm OEM unlocking is greyed on and 'VaultKeeper' is satisfied by rebooting once with internet

## Notes

- Samsung has no fastboot. Flashing uses Heimdall (download mode) or an Odin tar.
- Flashing a patched image trips the Knox warranty bit permanently. Samsung Pay, Secure Folder and Knox features stop working.
- US carrier and Snapdragon variants (SM-xxxxU, U1, W) have no OEM unlocking; bootloader cannot be unlocked.
