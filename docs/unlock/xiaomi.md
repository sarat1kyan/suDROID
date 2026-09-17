# Xiaomi / Redmi / POCO

Automated by the tool: no, guided.
Wipes data: yes.
Flash backend: fastboot.
Reference: https://en.miui.com/unlock/

## Steps

1. Sign in to a Mi account on the phone (Settings > Mi Account)
2. Developer options > Mi Unlock status > Add account and device (needs mobile data, not WiFi)
3. Wait the account binding period (72 hours to 30 days depending on region and HyperOS version)
4. On a Windows PC install Mi Unlock Tool, sign in with the same Mi account
5. Power off, hold Volume Down + Power to enter fastboot, connect, click Unlock
6. Device wipes. Re-enable USB debugging, then run sudroid root

## Notes

- Xiaomi unlock is account-bound and only possible through Mi Unlock Tool on Windows. The tool cannot automate it.
