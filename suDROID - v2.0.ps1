$logfile = "rooting_process_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
Start-Transcript -Path $logfile

Write-Host "Starting the Android Rooting Process..." -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Blue

Write-Host "
IMPORTANT NOTICE: Rooting your Android device carries certain risks.
Make sure you understand the steps involved, proceed with caution, and ensure you have a backup of important data.
Connect your Android device to your computer via USB and make sure USB debugging is enabled.
This script is provided 'as-is' without warranty. Use at your own risk.
" -ForegroundColor Red

do {
    $response = Read-Host "To proceed, type Y. For help enabling USB debugging, type H. To exit, type N"
    switch ($response.ToUpper()) {
        'Y' { break }
        'H' {
            Write-Host "Please follow these steps to enable USB debugging on your Android device:" -ForegroundColor Cyan
            Write-Host " 1. Open 'Settings' > 'About Phone' and tap 'Build number' seven times to enable developer options." -ForegroundColor Yellow
            Write-Host " 2. Return to 'Settings' > 'Developer options' and enable 'USB debugging'." -ForegroundColor Yellow
            Write-Host " 3. Connect your device to your computer via USB." -ForegroundColor Yellow
        }
        'N' { Exit }
        default { Write-Host "Invalid input. Please type Y, H, or N." -ForegroundColor Red }
    }
} until ($response -match '^[Yy]$')

function Handle-Error {
    Write-Host "Oops! Something went wrong during the process. Please check the log file for details: $logfile" -ForegroundColor Red
    Stop-Transcript
    Exit 1
}

Write-Host "Setting up environment for rooting..." -ForegroundColor Yellow
$patchingPath = Join-Path -Path $PWD -ChildPath "patching_process"
if (Test-Path -Path $patchingPath) { Remove-Item -Path $patchingPath -Recurse }
New-Item -ItemType Directory -Path $patchingPath | Out-Null
Set-Location -Path $patchingPath

Write-Host "Verifying if adb and fastboot are installed..." -ForegroundColor Green
$adb = Get-Command "adb.exe" -ErrorAction SilentlyContinue
$fastboot = Get-Command "fastboot.exe" -ErrorAction SilentlyContinue
if (-not $adb -or -not $fastboot) {
    Write-Host "adb or fastboot is not installed or not accessible in the PATH. Please install them before proceeding." -ForegroundColor Red
    Handle-Error
}

Write-Host "Checking device connection and bootloader status..." -ForegroundColor Cyan
& adb wait-for-device
if ($LASTEXITCODE -ne 0) {
    Write-Host "Device not connected. Ensure USB debugging is enabled and the device is connected." -ForegroundColor Red
    Handle-Error
}

$bootloaderStatus = & adb shell getprop ro.boot.flash.locked | Out-String
$bootloaderStatus = $bootloaderStatus.Trim()
if ($bootloaderStatus -eq "1") {
    Write-Host "Your device's bootloader is locked. Please unlock it before proceeding with this script." -ForegroundColor Red
    Handle-Error
}
Write-Host "Device connected successfully and bootloader is unlocked." -ForegroundColor Green

$magiskVersion = "v27.0"
$magiskURL = "https://github.com/topjohnwu/Magisk/releases/download/${magiskVersion}/Magisk-${magiskVersion}.zip"
$magiskFile = "magisk.zip"

Write-Host "Downloading Magisk version $magiskVersion..." -ForegroundColor Cyan
Invoke-WebRequest -Uri $magiskURL -OutFile $magiskFile -UseBasicParsing
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to download Magisk. Please check your internet connection." -ForegroundColor Red
    Handle-Error
}

Write-Host "Extracting Magisk files..." -ForegroundColor Cyan
Expand-Archive -Path $magiskFile -DestinationPath magisk -Force
Remove-Item -Path $magiskFile

Write-Host "Preparing to retrieve and back up the device's boot image..." -ForegroundColor Cyan
$bootImgPath = & adb shell find / -name 'boot.img' 2>$null | Out-String
$bootImgPath = $bootImgPath.Trim()
if (-not $bootImgPath) {
    $bootImgPath = Read-Host "Could not locate boot.img automatically. Please provide the path manually"
}

& adb pull $bootImgPath
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to retrieve boot.img from the device." -ForegroundColor Red
    Handle-Error
}

$backupPath = Join-Path -Path $PWD -ChildPath "backup_$(Get-Date -Format 'yyyyMMdd')"
New-Item -ItemType Directory -Path $backupPath | Out-Null
Copy-Item -Path "boot.img" -Destination "$backupPath\boot.img.bak"

Write-Host "Patching boot image with Magisk..." -ForegroundColor Cyan
$magiskFile = Get-ChildItem -Path "magisk" -Filter "magisk*"
& $magiskFile.FullName --boot-image boot.img patched_boot.img
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to patch boot image with Magisk." -ForegroundColor Red
    Handle-Error
}

Write-Host "Rebooting device to fastboot and flashing the patched boot image..." -ForegroundColor Cyan
& adb reboot bootloader
Start-Sleep -Seconds 15
& fastboot flash boot patched_boot.img
Start-Sleep -Seconds 10
& fastboot reboot

Write-Host "Cleaning up temporary files and directories..." -ForegroundColor Yellow
Set-Location -Path $PWD
Remove-Item -Path $patchingPath -Recurse

Write-Host "Rooting process completed successfully! A backup of your original boot image is saved in the backup folder for recovery." -ForegroundColor Green

Stop-Transcript