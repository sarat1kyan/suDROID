#!/bin/bash

CONFIG_FILE="root_config.cfg"
LOGFILE="rooting_process_$(date +"%Y%m%d_%H%M%S").log"
LOG_DIR="./logs"
BACKUP_DIR="./backups"
mkdir -p "$LOG_DIR" "$BACKUP_DIR"
find "$LOG_DIR" -type f -name "*.log" -mtime +30 -delete
exec > >(tee -a "$LOG_DIR/$LOGFILE") 2>&1
exec 2>&1

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

MAGISK_VERSION="v27.0"
MAGISK_RELEASE_URL="https://api.github.com/repos/topjohnwu/Magisk/releases/latest"
MAGISK_DOWNLOAD_URL="https://github.com/topjohnwu/Magisk/releases/download"
MIN_BATTERY_LEVEL=50
RETRY_LIMIT=3
INTERACTIVE=true

if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
fi

cat <<EOF
${CYAN}${BOLD}Starting the Android Rooting Process... $(date +"%Y-%m-%d %H:%M:%S")${NC}
${BLUE}================================================================================${NC}
${RED}${BOLD}IMPORTANT NOTICE: Rooting your Android device carries certain risks.
Ensure you understand the steps, proceed with caution, and back up all important data.
${NC}
EOF

log_message() {
    local msg="$1"
    local level="${2:-INFO}"
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    printf "[$timestamp] [%s] %s\n" "$level" "$msg" | tee -a "$LOG_DIR/$LOGFILE"
}

check_internet() {
    log_message "Checking internet connectivity..." "INFO"
    for ((i=1; i<=RETRY_LIMIT; i++)); do
        if curl -Is "http://google.com" >/dev/null 2>&1; then
            log_message "Internet connection verified." "SUCCESS"
            return
        fi
        log_message "No internet detected. Retry $i/$RETRY_LIMIT..." "WARNING"
        sleep 5
    done
    log_message "Failed to detect internet connection after $RETRY_LIMIT attempts." "ERROR"
    exit 1
}

check_device_compatibility() {
    local model=$(adb shell getprop ro.product.model | tr -d '\r')
    local android_version=$(adb shell getprop ro.build.version.release | tr -d '\r')
    log_message "Device Model: $model | Android Version: $android_version" "INFO"
    case "$model" in
        "Pixel 5"|"Pixel 4a")
            log_message "Device compatibility verified for Pixel series." "SUCCESS"
            ;;
        "Samsung Galaxy S10")
            log_message "Detected Samsung Galaxy device. Note: Specific steps may apply for Samsung devices." "INFO"
            ;;
        "OnePlus 8")
            log_message "Detected OnePlus device. Compatibility verified." "SUCCESS"
            ;;
        *)
            log_message "Warning: This device ($model) may not be fully supported." "WARNING"
            ;;
    esac
}

get_latest_magisk_version() {
    log_message "Retrieving the latest Magisk version..." "INFO"
    if ! latest_version=$(curl -s "$MAGISK_RELEASE_URL" | jq -r '.tag_name'); then
        log_message "Failed to fetch latest Magisk version. Using default $MAGISK_VERSION." "WARNING"
    else
        MAGISK_VERSION="${latest_version:-$MAGISK_VERSION}"
    fi
    log_message "Using Magisk version $MAGISK_VERSION." "INFO"
}

setup_environment() {
    log_message "Setting up environment and installing dependencies..." "INFO"
    if command -v apt >/dev/null 2>&1; then
        sudo apt update && sudo apt install -y adb fastboot curl wget unzip zip jq
    elif command -v dnf >/dev/null 2>&1; then
        sudo dnf install -y android-tools curl wget unzip zip jq
    elif command -v pacman >/dev/null 2>&1; then
        sudo pacman -S --noconfirm android-tools curl wget unzip zip jq
    elif command -v zypper >/dev/null 2>&1; then
        sudo zypper install -y android-tools curl wget unzip zip jq
    else
        log_message "Unsupported Linux distribution detected. Install required tools manually." "ERROR"
        exit 1
    fi
}

verify_adb_fastboot() {
    log_message "Verifying adb and fastboot installation..." "INFO"
    for cmd in adb fastboot; do
        if ! command -v "$cmd" &> /dev/null; then
            log_message "$cmd not found. Ensure it is installed and accessible in your PATH." "ERROR"
            exit 1
        fi
    done
    log_message "Ensuring device connectivity and USB debugging..." "INFO"
    adb wait-for-device || { log_message "Device not detected. Enable USB debugging and reconnect device." "ERROR"; exit 1; }
}

check_battery_level() {
    log_message "Checking device battery level..." "INFO"
    for ((i=1; i<=RETRY_LIMIT; i++)); do
        battery_level=$(adb shell dumpsys battery | grep -m1 'level:' | awk '{print $2}')
        if [[ -n "$battery_level" && "$battery_level" -ge $MIN_BATTERY_LEVEL ]]; then
            log_message "Battery level sufficient for rooting process." "SUCCESS"
            return
        fi
        log_message "Battery level below $MIN_BATTERY_LEVEL%. Retry $i/$RETRY_LIMIT..." "WARNING"
        sleep 5
    done
    log_message "Battery level too low after $RETRY_LIMIT attempts. Charge device before proceeding." "ERROR"
    exit 1
}

check_and_unlock_bootloader() {
    local bootloader_status
    bootloader_status=$(adb shell getprop ro.boot.flash.locked | tr -d '\r')
    if [[ "$bootloader_status" == "1" ]]; then
        log_message "Bootloader is locked. Attempting to unlock bootloader..." "WARNING"
        adb reboot bootloader
        sleep 5
        fastboot oem unlock || fastboot flashing unlock || {
            log_message "Unable to unlock bootloader. Please unlock manually and re-run the script." "ERROR"
            exit 1
        }
    else
        log_message "Bootloader is already unlocked." "SUCCESS"
    fi
}

backup_user_data() {
    log_message "Creating full device backup (apps, settings, media)..." "INFO"
    adb backup -apk -all -f "$BACKUP_DIR/device_backup.ab" || {
        log_message "Backup failed. Ensure sufficient storage space and ADB permissions." "ERROR"
        exit 1
    }
    log_message "Backup completed. Saved to $BACKUP_DIR/device_backup.ab" "SUCCESS"
}

download_magisk() {
    local download_url="${MAGISK_DOWNLOAD_URL}/${MAGISK_VERSION}/Magisk-${MAGISK_VERSION}.zip"
    log_message "Downloading Magisk version $MAGISK_VERSION..." "INFO"
    for ((i=1; i<=RETRY_LIMIT; i++)); do
        if wget -q "$download_url" -O "magisk.zip"; then
            log_message "Magisk downloaded successfully." "SUCCESS"
            break
        else
            log_message "Failed to download Magisk. Retry $i/$RETRY_LIMIT..." "WARNING"
            sleep 5
        fi
    done
    unzip -j "magisk.zip" -d magisk && rm "magisk.zip"
}

backup_images() {
    log_message "Backing up boot and system images..." "INFO"
    if ! adb pull /dev/block/by-name/boot boot.img || ! adb pull /dev/block/by-name/system system.img; then
        log_message "Failed to back up images." "ERROR"
        exit 1
    fi
    mkdir -p "../backup_$(date +"%Y%m%d")" && cp boot.img "../backup_$(date +"%Y%m%d")/boot.img.bak"
}

patch_boot_image() {
    log_message "Patching boot image with Magisk..." "INFO"
    chmod +x magisk/*
    local magisk_file
    magisk_file=$(find magisk -name 'magisk*')
    if ! "$magisk_file" --boot-image boot.img patched_boot.img; then
        log_message "Failed to patch boot image with Magisk." "ERROR"
        exit 1
    fi
}

flash_patched_image() {
    read -p "$(echo -e "${CYAN}Ready to flash patched image. Proceed? [Y/N]: ${NC}") " confirm
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        log_message "Flashing patched boot image..." "INFO"
        adb reboot bootloader && sleep 15
        fastboot flash boot patched_boot.img && sleep 10
        fastboot reboot
    else
        log_message "Flashing aborted by user." "WARNING"
    fi
}

verify_root_access() {
    log_message "Verifying root access..." "INFO"
    if adb shell su -c 'echo "Root access verified!"' >/dev/null 2>&1; then
        log_message "Root access successfully verified." "SUCCESS"
    else
        log_message "Root verification failed." "ERROR"
    fi
}

restore_user_data() {
    log_message "Restoring user data from backup..." "INFO"
    adb restore "$BACKUP_DIR/device_backup.ab" || {
        log_message "Restore failed. Ensure permissions and ADB connection." "ERROR"
        exit 1
    }
}

cleanup() {
    log_message "Cleaning up temporary files and directories..." "INFO"
    cd .. && rm -rf patching_process
    log_message "Rooting process completed successfully. Backup files available in $BACKUP_DIR." "SUCCESS"
}

main() {
    echo -e "${CYAN}Choose an option:${NC}"
    echo "1. Check Internet Connectivity"
    echo "2. Setup Environment"
    echo "3. Verify Device Connectivity"
    echo "4. Check Battery Level"
    echo "5. Backup User Data"
    echo "6. Check and Unlock Bootloader"
    echo "7. Download Magisk"
    echo "8. Backup Images"
    echo "9. Patch Boot Image"
    echo "10. Flash Patched Image"
    echo "11. Verify Root Access"
    echo "12. Restore User Data"
    echo "13. Clean Up and Exit"
    
    while true; do
        read -rp "Enter choice: " choice
        case "$choice" in
            1) check_internet ;;
            2) setup_environment ;;
            3) verify_adb_fastboot ;;
            4) check_battery_level ;;
            5) backup_user_data ;;
            6) check_and_unlock_bootloader ;;
            7) download_magisk ;;
            8) backup_images ;;
            9) patch_boot_image ;;
            10) flash_patched_image ;;
            11) verify_root_access ;;
            12) restore_user_data ;;
            13) cleanup; exit ;;
            *) log_message "Invalid option. Please select a valid choice." "WARNING" ;;
        esac
    done
}

main
