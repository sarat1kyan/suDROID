#!/bin/bash

echo "here we go..."

# Display disclaimer and prompt for user input
echo "*******************************************************************************************************"
echo "IMPORTANT NOTICE: Rooting your Android device can be risky"
echo "and it's important to proceed with caution and follow the necessary steps carefully."
echo "You also need to make sure that your Android device is connected to your computer via USB"
echo "and that USB debugging is enabled."
echo "use this script at your own risk, i'm not responsible for the shit that happened"
echo "*******************************************************************************************************"
while true; do
    read -p "If you understand the risks and want to proceed, press Y. Press H for help with enabling USB debugging. Press N to exit. " yn
    case $yn in
        [Yy]* )
            break;;
        [Hh]* )
            echo ""
            echo "Please follow these steps to enable USB debugging on your Android device:"
            echo "1. Go to 'Settings' on your Android device."
            echo "2. Scroll down and select 'System' (or 'About Phone' depending on your device)."
            echo "3. Scroll down to 'Build number' and tap it seven times to enable developer options."
            echo "4. Go back to 'Settings' and select 'Developer options'."
            echo "5. Turn on 'USB debugging' and connect your Android device to your computer via USB."
            echo ""
            ;;
        [Nn]* )
            exit;;
        * )
            echo "Please answer Y, H, or N.";;
    esac
done



# Create a new directory called "patching_process"
rm -rf patching_process && mkdir patching_process > /dev/null 2>&1

# Move into the newly created directory
cd patching_process > /dev/null 2>&1


# Check the Linux distribution and install the necessary packages

            
echo "now we are checking the Linux distribution and installing the necessary packages"
            

if command -v apt >/dev/null 2>&1; then
    sudo apt update && sudo apt install -y adb fastboot curl wget unzip zip > /dev/null 2>&1
elif command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y android-tools curl unzip zip > /dev/null 2>&1
elif command -v pacman >/dev/null 2>&1; then
    sudo pacman -S --noconfirm android-tools curl wget unzip zip > /dev/null 2>&1
elif command -v zypper >/dev/null 2>&1; then
    sudo zypper install -y android-tools curl wget unzip zip > /dev/null 2>&1
elif command -v yum >/dev/null 2>&1; then
    sudo yum install -y android-tools curl wget unzip zip > /dev/null 2>&1
else
    echo "Unsupported Linux distribution"
    exit 1
fi

# Check for adb and fastboot installation
echo "checking if adb and fastboot installed"
if ! command -v adb &> /dev/null || ! command -v fastboot &> /dev/null; then
    echo "adb and fastboot not found. Please make sure they are installed and added to your PATH."
    exit 1
fi

# Connect Android device via USB and check if it's connected
echo "Please connect your Android device via USB and make sure USB debugging is enabled."
            
sleep 45
adb wait-for-device
if [ $? -eq 0 ]; then
  echo "Device connected successfully"
              
else
  echo "Device not connected. Please make sure that the USB cable and the device port is working and USB debugging is enabled."
              
  exit 1
fi

# Enable developer options on the Android device
echo "Enabling developer options..."
            
adb shell settings put global development_settings_enabled 1 > /dev/null 2>&1
sleep 20

# Enable USB debugging on the Android device
echo "Checking and (if needed) Enabling the USB debugging..."
            
adb shell settings put global adb_enabled 1 > /dev/null 2>&1
sleep 20

# Reboot the Android device into bootloader mode
echo "Rebooting into bootloader mode..."
            
adb reboot bootloader > /dev/null 2>&1
sleep 90

# Download and install Magisk
   echo "Downloading Magisk..."
               
    wget https://github.com/topjohnwu/Magisk/releases/download/v23.0/Magisk-v23.0.zip -O magisk.zip > /dev/null 2>&1
    sleep 20
    echo "Installing Magisk..."
                
    unzip -j magisk.zip -d magisk > /dev/null 2>&1
    sleep 20
    rm magisk.zip
   

# Export the boot.img from the connected Android device
echo "Exporting boot.img from the connected Android device..."
     
echo "Check if boot.img file exists in any possible directory"

# Search for boot.img file on the device
boot_img_path="$(adb shell find / -name 'boot.img' 2>/dev/null | tr -d '\r')"
if [ -z "$boot_img_path" ]; then
  echo "Could not find boot.img file on the device."
  exit 1
fi

# Export boot.img file to working directory
echo "Exporting boot.img from device..."
adb pull "$boot_img_path" >/dev/null 2>&1
if [ $? -ne 0 ]; then
  echo "Failed to export boot.img. Please provide the path to your boot.img file: "
  read boot_img_path
else
  echo "boot.img exported successfully."
  boot_img_path="./boot.img"
  
  echo "Backup proccess for the the boot.img was started, so you can roll-back if something shittttyyy happaned"
  mkdir -p ../"backup_$(date +"%Y%m%d")" && cp ./boot.img ../"backup_$(date +"%Y%m%d")"/boot.img.bak
  
fi

# Patch boot.img with Magisk
echo "Patching boot.img with Magisk..."
magisk --version >/dev/null 2>&1
if [ $? -eq 0 ]; then
chmod +x magisk*
  magisk --boot-image "$boot_img_path" "patched_boot.img" >/dev/null 2>&1
else
  echo "Magisk not found. Please download and install it manually from https://github.com/topjohnwu/Magisk/releases."
  exit 1
fi


# If boot.img is not found, prompt the user to provide it
if [ -z "$boot_img_path" ]; then
  read -p "Please provide the path to your boot.img file: " boot_img_path
fi

# Reboot device into fastboot mode
echo "Rebooting device into fastboot mode..."
adb reboot bootloader >/dev/null 2>&1

# Flash patched boot.img to device
echo "Flashing patched boot.img to device..."
fastboot flash boot "patched_boot.img" >/dev/null 2>&1
sleep 20

# Reboot device
echo "Rebooting device..."
fastboot reboot >/dev/null 2>&1

# Clean up the downloaded files
echo "Cleaning up..."
            
rm magisk.zip
cd .. && rm -rf patching_process

# Clean up installed packages
if [[ -n "${cleanup_cmd}" ]]; then
    echo "Removing installed packages..."
    ${cleanup_cmd}
fi

echo "Done!"
echo "If you have any problems contact with me"
echo "Also you can always recover from your original boot.img that is located in the backup directory (named as boot.img.bak)"
