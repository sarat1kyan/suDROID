#!/bin/bash
LOGFILE="rooting_process_$(date +"%Y%m%d_%H%M%S").log"
exec > >(tee -a "$LOGFILE") 2>&1
exec 2>&1

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${CYAN}${BOLD}Starting the Android Rooting Process... $(date +"%Y-%m-%d %H:%M:%S")${NC}"
echo -e "${BLUE}================================================================================${NC}"

cat <<EOF
${RED}${BOLD}*******************************************************************************************************
IMPORTANT NOTICE: Rooting your Android device carries certain risks.
Make sure you understand the steps involved, proceed with caution, and ensure you have a backup of important data.
Connect your Android device to your computer via USB and make sure USB debugging is enabled.
This script is provided "as-is" without warranty. Use at your own risk.
*******************************************************************************************************${NC}
EOF

while true; do
    read -p "$(echo -e "${CYAN}To proceed, type ${GREEN}Y${CYAN}. For help enabling USB debugging, type ${YELLOW}H${CYAN}. To exit, type ${RED}N${CYAN}.${NC} ") " yn
    case $yn in
        [Yy]* ) break;;
        [Hh]* )
            echo -e "${CYAN}\nPlease follow these steps to enable USB debugging on your Android device:${NC}"
            echo -e " ${BLUE}1.${NC} Open 'Settings' on your device, go to 'About Phone', and tap 'Build number' seven times to unlock developer options."
            echo -e " ${BLUE}2.${NC} Go back to 'Settings' and select 'Developer options'."
            echo -e " ${BLUE}3.${NC} Enable 'USB debugging' and connect your device to your computer via USB.\n"
            ;;
        [Nn]* ) exit;;
        * ) echo -e "${RED}Invalid input. Please type Y, H, or N.${NC}";;
    esac
done

handle_error() {
    echo -e "${RED}Oops! Something went wrong during the process. Please check the log file for details: $LOGFILE${NC}"
    exit 1
}

trap 'handle_error' ERR

setup_environment() {
    echo -e "${YELLOW}Setting up environment for rooting...${NC}"
    rm -rf patching_process && mkdir patching_process
    cd patching_process || { echo -e "${RED}Failed to access the required directory. Exiting.${NC}"; exit 1; }

    echo -e "${GREEN}Checking Linux distribution and installing necessary packages...${NC}"
    if command -v apt >/dev/null 2>&1; then
        sudo apt update && sudo apt install -y adb fastboot curl wget unzip zip
    elif command -v dnf >/dev/null 2>&1; then
        sudo dnf install -y android-tools curl wget unzip zip
    elif command -v pacman >/dev/null 2>&1; then
        sudo pacman -S --noconfirm android-tools curl wget unzip zip
    elif command -v zypper >/dev/null 2>&1; then
        sudo zypper install -y android-tools curl wget unzip zip
    elif command -v yum >/dev/null 2>&1; then
        sudo yum install -y android-tools curl wget unzip zip
    else
        echo -e "${RED}Unsupported Linux distribution detected. Please install the required tools manually.${NC}"
        exit 1
    fi
}

check_adb_fastboot() {
    echo -e "${GREEN}Verifying if adb and fastboot are installed...${NC}"
    for cmd in adb fastboot; do
        if ! command -v $cmd &> /dev/null; then
            echo -e "${RED}$cmd not found. Please ensure it is installed and accessible in your PATH.${NC}"
            exit 1
        fi
    done
}

check_device() {
    echo -e "${CYAN}Checking device connection and bootloader status...${NC}"
    adb wait-for-device || { echo -e "${RED}Device not detected. Ensure USB debugging is enabled and the device is connected.${NC}"; exit 1; }
    
    bootloader_status=$(adb shell getprop ro.boot.flash.locked | tr -d '\r')
    if [ "$bootloader_status" = "1" ]; then
        echo -e "${RED}Your device's bootloader is locked.${NC}"
        read -p "Do you need help unlocking your bootloader? (y/n): " help_unlock
        if [[ "$help_unlock" =~ ^[Yy]$ ]]; then
            device_brand=$(adb shell getprop ro.product.brand | tr -d '\r')
            device_model=$(adb shell getprop ro.product.model | tr -d '\r')
            
            case "$device_brand" in
                "xiaomi"|"redmi")
                    echo -e "${YELLOW}For Xiaomi devices, visit the official Mi Unlock page to download the unlocking tool.${NC}"
                    ;;
                "oneplus")
                    echo -e "${YELLOW}For OnePlus devices, follow instructions on the official OnePlus support page to unlock your bootloader.${NC}"
                    ;;
                "samsung")
                    echo -e "${YELLOW}Samsung USA devices typically require a Token. I can't help with this. Else If you are in Europe you can unlock it easily, just search online for your device root method${NC}"
                    ;;
                "asus")
                    echo -e "${YELLOW}ASUS provides an unlock tool; visit the official ASUS support page.${NC}"
                    ;;
                "motorola")
                    echo -e "${YELLOW}Motorola provides official unlock instructions; visit the Motorola support page.${NC}"
                    ;;
                "google")
                    echo -e "${YELLOW}Google Pixel devices can typically be unlocked via fastboot; run:\n fastboot flashing unlock${NC}"
                    ;;
                *)
                    chip_vendor=$(adb shell getprop ro.hardware.chipname | tr -d '\r')
                    if [[ "$chip_vendor" == *"mt"* ]]; then
                        echo -e "${CYAN}Detected MediaTek chipset.${NC} You can try using the ${GREEN}mtkclient${NC} tool for unlocking:https://github.com/bkerler/mtkclient"
                    elif [[ "$chip_vendor" == *"unisoc"* ]]; then
                        echo -e "${CYAN}Detected Unisoc chipset.${NC} For Unisoc devices, try using Hovatek's Identifier Token method:https://www.hovatek.com/forum/thread-32287.html, or ${GREEN}CVE-2022-38691${NC} on GitHub:https://github.com/TomKing062/CVE-2022-38694_unlock_bootloader. If you are so lucky to have an engeneeing firmware for the device flash it and then you can flash GSIs without unlocking the bootloader but on A11 and before only, more info:https://adshnk.com/Jd4w9l"
                    else
                        echo -e "${YELLOW}For other brands or chipsets, please refer to official support, or search for device-specific unlock guides online.${NC}"
                    fi
                    ;;
            esac
            exit 1
        else
            echo -e "${RED}Bootloader must be unlocked before proceeding. Exiting.${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}Device connected successfully and bootloader is unlocked.${NC}"
    fi
}

flash_patched_image() {
    echo -e "${CYAN}Copy the patched boot image on /storage/emulated/0/Download to the script folder and rename it as boot.img.${NC}"
    echo -e "${CYAN}Rebooting device to fastboot and flashing the patched boot image...${NC}"
    adb reboot bootloader && sleep 15
    fastboot flash boot boot.img && sleep 10
    fastboot reboot
}

echo -e "${GREEN}Choose your root method:${NC}"
echo -e "${GREEN}1. Magisk${NC}"
echo -e "${GREEN}2. Apatch${NC}"
echo -e "${GREEN}3. KernelSU${NC}"
read -p "Enter the number of your choice: " root_method_choice

case $root_method_choice in
    1) 
    echo -e "${CYAN}You selected Magisk.${NC}"
    echo -e "${YELLOW}To use Magisk, install the Magisk app, extract the boot image from your device stock firmware (if possible it must be the same version as your device software, else full flash it), copy it to the device and follow the in-app instructions to patch your boot image.${NC}"
    read -p "press enter when ready"
    flash_patched_image
    ;;

2) 
    echo -e "${CYAN}You selected Apatch.${NC}"
    echo -e "${YELLOW}To use Apatch, install the Apatch app, extract the boot image from your device stock firmware (if possible it must be the same version as your device software, else full flash it), copy it to the device and follow the in-app instructions to patch your boot image.${NC}"
    read -p "press enter when ready"
    flash_patched_image
    ;;

3) 
    echo -e "${CYAN}You selected KernelSU.${NC}"
    echo -e "${YELLOW}To root with KernelSU, download the appropriate KernelSU-patched boot image for your device.${NC}"
    echo -e "Then, you can flash it using one of these methods:"
    echo -e "  ${GREEN}- From TWRP: flash the boot image directly.${NC}"
    echo -e "  ${GREEN}- Via fastboot:${NC}"
    echo -e "    1. Reboot to bootloader: ${BOLD}adb reboot bootloader${NC}"
    echo -e "    2. Flash the image: ${BOLD}fastboot flash boot boot.img${NC}"
    read -p "press enter when ready"
    flash_patched_image
    ;;
    *) 
        echo -e "${RED}Invalid selection. Exiting.${NC}"
        exit 1
        ;;
esac

setup_environment
check_adb_fastboot
check_device
