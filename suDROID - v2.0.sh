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
        echo -e "${RED}Your device's bootloader is locked. Please unlock it before proceeding with this script.${NC}"
        exit 1
    fi

    echo -e "${GREEN}Device connected successfully and bootloader is unlocked.${NC}"
}

download_magisk() {
    MAGISK_VERSION="v27.0"
    MAGISK_URL="https://github.com/topjohnwu/Magisk/releases/download/${MAGISK_VERSION}/Magisk-${MAGISK_VERSION}.zip"
    MAGISK_FILE="magisk.zip"
    
    echo -e "${CYAN}Downloading Magisk version $MAGISK_VERSION...${NC}"
    wget -q "$MAGISK_URL" -O "$MAGISK_FILE" || { echo -e "${RED}Failed to download Magisk. Please check your internet connection.${NC}"; exit 1; }
    
    echo -e "${CYAN}Extracting Magisk files...${NC}"
    unzip -j "$MAGISK_FILE" -d magisk && rm "$MAGISK_FILE"
}

patch_boot_image() {
    echo -e "${CYAN}Preparing to retrieve and back up the device's boot image...${NC}"
    boot_img_path="$(adb shell find / -name 'boot.img' 2>/dev/null | tr -d '\r')"
    if [ -z "$boot_img_path" ]; then
        read -p "Could not locate boot.img automatically. Please provide the path manually: " boot_img_path
    fi
    
    adb pull "$boot_img_path" || { echo -e "${RED}Failed to retrieve boot.img from the device.${NC}"; exit 1; }
    mkdir -p "../backup_$(date +"%Y%m%d")" && cp boot.img "../backup_$(date +"%Y%m%d")/boot.img.bak"
    
    echo -e "${CYAN}Patching boot image with Magisk...${NC}"
    chmod +x magisk/*
    magisk_file=$(find magisk -name 'magisk*')
    $magisk_file --boot-image boot.img patched_boot.img || { echo -e "${RED}Failed to patch boot image with Magisk.${NC}"; exit 1; }
}

flash_patched_image() {
    echo -e "${CYAN}Rebooting device to fastboot and flashing the patched boot image...${NC}"
    adb reboot bootloader && sleep 15
    fastboot flash boot patched_boot.img && sleep 10
    fastboot reboot
}

cleanup() {
    echo -e "${YELLOW}Removing temporary files and directories...${NC}"
    cd .. && rm -rf patching_process
    echo -e "${GREEN}Rooting process completed successfully!${NC} ${CYAN}A backup of your original boot image is saved in the backup folder for recovery.${NC}"
}

main() {
    setup_environment
    check_adb_fastboot
    check_device
    download_magisk
    patch_boot_image
    flash_patched_image
    cleanup
}

main