@echo off

REM Check if script is being run as administrator
NET SESSION >NUL 2>&1
IF %ERRORLEVEL% NEQ 0 (
  echo This script must be run as administrator.
  pause
  exit /B
)

REM Install necessary tools
IF NOT EXIST "C:\adb\adb.exe" (
  echo Installing necessary tools...
  mkdir C:\adb
  curl -sSLo C:\adb\adb.zip https://dl.google.com/android/repository/platform-tools-latest-windows.zip
  tar -xf C:\adb\adb.zip -C C:\adb
  del C:\adb\adb.zip
  echo PATH=%PATH%;C:\adb >> %USERPROFILE%\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\addpath.bat
)

REM Search for boot.img file on the device
set "boot_img_path="
for /f "delims=" %%i in ('adb shell "find / -name boot.img" 2^>nul ^| tr -d "\r"') do (
  set "boot_img_path=%%i"
)
if not defined boot_img_path (
  echo Could not find boot.img file on the device.
  pause
  exit /B
)

REM Export boot.img file to working directory
echo Exporting boot.img from device...
adb pull "%boot_img_path%" >NUL 2>&1
if %ERRORLEVEL% NEQ 0 (
  echo Failed to export boot.img. Please provide the path to your boot.img file:
  set /p boot_img_path=
) else (
  echo boot.img exported successfully.
  set "boot_img_path=%CD%\boot.img"
)

REM Patch boot.img with Magisk
echo Patching boot.img with Magisk...
magisk --version >NUL 2>&1
if %ERRORLEVEL% EQU 0 (
  magisk --boot-image "%boot_img_path%" "patched_boot.img" >NUL 2>&1
) else (
  echo Magisk not found. Please download and install it from https://github.com/topjohnwu/Magisk/releases.
  pause
  exit /B
)

REM Reboot device into fastboot mode
echo Rebooting device into fastboot mode...
adb reboot bootloader >NUL 2>&1

REM Flash patched boot.img to device
echo Flashing patched boot.img to device...
fastboot flash boot "patched_boot.img" >NUL 2>&1

REM Reboot device
echo Rebooting device...
fastboot reboot >NUL 2>&1

echo Done.
pause

