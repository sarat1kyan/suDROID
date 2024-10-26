# Set up logging
$LogFile = "rooting_process_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
Start-Transcript -Path $LogFile -Append

# Define colors for output
$RED = "`e[31m"
$GREEN = "`e[32m"
$YELLOW = "`e[33m"
$BLUE = "`e[34m"
$CYAN = "`e[36m"
$BOLD = "`e[1m"
$NC = "`e[0m"

# Starting message
Write-Host "${CYAN}${BOLD}Starting the Android Rooting Process... $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')${NC}"
Write-Host "${BLUE}================================================================================${NC}"

Write-Host @"
${RED}${BOLD}*******************************************************************************************************
IMPORTANT NOTICE: Rooting your Android device carries certain risks.
Make sure you understand the steps involved, proceed with caution, and ensure you have a backup of important data.
Connect your Android device to your computer via USB and make sure USB debugging is enabled.
This script is provided "as-is" without warranty. Use at your own risk.
*******************************************************************************************************${NC}
"@

# Confirmation prompt
do {
    $userInput = Read-Host "${CYAN}To proceed, type ${GREEN}Y${CYAN}. For help enabling USB debugging, type ${YELLOW}H${CYAN}. To exit, type ${RED}N${CYAN}.${NC}"
    switch ($userInput.ToUpper()) {
        "Y" { break }
        "H" {
            Write-Host "${CYAN}Follow these steps to enable USB debugging on your Android device:${NC}"
            Write-Host "${BLUE}1.${NC} Open 'Settings' on your device, go to 'About Phone', and tap 'Build number' seven times to unlock developer options."
            Write-Host "${BLUE}2.${NC} Go back to 'Settings' and select 'Developer options'."
            Write-Host "${BLUE}3.${NC} Enable 'USB debugging' and connect your device to your computer via USB."
        }
        "N" { exit }
        default { Write-Host "${RED}Invalid input. Please type Y, H, or N.${NC}" }
    }
} until ($userInput -match "^[YyNn]$")

# Error handler
function Handle-Error {
    Write-Host "${RED}Oops! Something went wrong during the process. Please check the log file for details: $LogFile${NC}"
    Stop-Transcript
    exit 1
}

# Environment setup function
function Setup-Environment {
    Write-Host "${YELLOW}Setting up environment for rooting...${NC}"
    if (-not (Test-Path "patching_process")) {
        New-Item -Path "patching_process" -ItemType Directory
    }
    Set-Location -Path "patching_process"

    Write-Host "${GREEN}Checking if adb and fastboot are installed...${NC}"
    if (-not (Get-Command adb -ErrorAction SilentlyContinue)) {
        Write-Host "${RED}adb not found. Please ensure it is installed and accessible in your PATH.${NC}"
        exit 1
    }
    if (-not (Get-Command fastboot -ErrorAction SilentlyContinue)) {
        Write-Host "${RED}fastboot not found. Please ensure it is installed and accessible in your PATH.${NC}"
        exit 1
    }
}

# Check device connection and bootloader status
function Check-Device {
    Write-Host "${CYAN}Checking device connection and bootloader status...${NC}"
    & adb wait-for-device

    $bootloaderStatus = (& adb shell getprop ro.boot.flash.locked).Trim()
    if ($bootloaderStatus -eq "1") {
        Write-Host "${RED}Your device's bootloader is locked.${NC}"
        $helpUnlock = Read-Host "Do you need help unlocking your bootloader? (y/n)"
        if ($helpUnlock -match "^[Yy]$") {
            $deviceBrand = (& adb shell getprop ro.product.brand).Trim()
            switch ($deviceBrand) {
                "xiaomi" { Write-Host "${YELLOW}For Xiaomi devices, visit the official Mi Unlock page to download the unlocking tool.${NC}" }
                "oneplus" { Write-Host "${YELLOW}For OnePlus devices, follow instructions on the official OnePlus support page.${NC}" }
                "samsung" { Write-Host "${YELLOW}Samsung USA devices typically require a Token. I can't help with this. Else If you are in Europe you can unlock it easily, just search online for your device root method${NC}" }
                "asus" { Write-Host "${YELLOW}ASUS provides an unlock tool; visit the official ASUS support page.${NC}" }
                "motorola" { Write-Host "${YELLOW}Motorola provides official unlock instructions; visit the Motorola support page.${NC}" }
                "google" { Write-Host "${YELLOW}Google Pixel devices can typically be unlocked via fastboot; run: fastboot flashing unlock${NC}" }
                default {
                    $chipVendor = (& adb shell getprop ro.hardware.chipname).Trim()
                    if ($chipVendor -match "mt") {
                        Write-Host "${CYAN}Detected MediaTek chipset. Try using the mtkclient tool for unlocking.${NC}"
                    } elseif ($chipVendor -match "unisoc") {
                        Write-Host "${CYAN}Detected Unisoc chipset. Use Hovatek's Identifier Token method:https://www.hovatek.com/forum/thread-32287.html, or CVE-2022-38691 on GitHub:https://github.com/TomKing062/CVE-2022-38694_unlock_bootloader.${NC}. If you are so lucky to have an engeneeing firmware for the device flash it and then you can flash GSIs without unlocking the bootloader but on A11 and before only"
                    } else {
                        Write-Host "${YELLOW}For other brands or chipsets, refer to official support, or search for device-specific unlock guides.${NC}"
                    }
                }
            }
            exit 1
        } else {
            Write-Host "${RED}Bootloader must be unlocked before proceeding. Exiting.${NC}"
            exit 1
        }
    } else {
        Write-Host "${GREEN}Device connected successfully and bootloader is unlocked.${NC}"
    }
}

# Flash patched boot image function
function Flash-PatchedImage {
    Write-Host "${CYAN}Copy the patched boot image to /storage/emulated/0/Download and rename it to boot.img.${NC}"
    Write-Host "${CYAN}Rebooting device to fastboot and flashing the patched boot image...${NC}"
    & adb reboot bootloader
    Start-Sleep -Seconds 15
    & fastboot flash boot boot.img
    Start-Sleep -Seconds 10
    & fastboot reboot
}

# Root method selection
Write-Host "${GREEN}Choose your root method:${NC}"
Write-Host "${GREEN}1. Magisk${NC}"
Write-Host "${GREEN}2. Apatch${NC}"
Write-Host "${GREEN}3. KernelSU${NC}"
$rootMethodChoice = Read-Host "Enter the number of your choice"

switch ($rootMethodChoice) {
    1 {
        Write-Host "${CYAN}You selected Magisk.${NC}"
        Write-Host "${YELLOW}Install the Magisk app, extract the boot image from your stock firmware, and follow in-app instructions to patch it.${NC}"
        Read-Host -Prompt "Press Enter when ready"
        Flash-PatchedImage
    }
    2 {
        Write-Host "${CYAN}You selected Apatch.${NC}"
        Write-Host "${YELLOW}Install the Apatch app, extract the boot image from your stock firmware, and follow in-app instructions to patch it.${NC}"
        Read-Host -Prompt "Press Enter when ready"
        Flash-PatchedImage
    }
    3 {
        Write-Host "${CYAN}You selected KernelSU.${NC}"
        Write-Host "${YELLOW}Download the appropriate KernelSU-patched boot image, and flash it using TWRP or fastboot.${NC}"
        Write-Host "${GREEN}1. From TWRP: flash the boot image directly."
        Write-Host "${GREEN}2. Via fastboot: Run 'adb reboot bootloader' and then 'fastboot flash boot boot.img'."
        Read-Host -Prompt "Press Enter when ready"
        Flash-PatchedImage
    }
    default {
        Write-Host "${RED}Invalid selection. Exiting.${NC}"
        exit 1
    }
}

# Execution of main functions
Setup-Environment
Check-Device
Stop-Transcript
