#!/bin/bash

clear

banner1() {
  local text="$@"
  local length=$(( ${#text} + 2 ))
  local line=$(printf '%*s' "$length" '' | tr ' ' '-')
  echo "+$line+"
  printf "| %s |\n" "$(date)"
  echo "+$line+"
  printf "|$bold%s$reset|\n" "$text"
  echo "+$line+"
}

# Check if script is being run as root
if [[ $EUID -ne 0 ]]; then
  banner1 "This script must be run as root."
  exit 1
fi

#clolors
white='\e[1;37m'
green='\e[0;32m'
blue='\e[1;34m'
red='\e[1;31m'
yellow='\e[1;33m' 
echo ""
echo ""
banner() {
	echo -e $'\e[1;33m\e[0m\e[1;37m       ██████  █    ██ ▓█████▄  ██▀███   ▒█████   ██▓▓█████▄    \e[0m'
	echo -e $'\e[1;33m\e[0m\e[1;37m     ▒██    ▒  ██  ▓██▒▒██▀ ██▌▓██ ▒ ██▒▒██▒  ██▒▓██▒▒██▀ ██▌   \e[0m'
	echo -e $'\e[1;33m\e[0m\e[1;37m     ░ ▓██▄   ▓██  ▒██░░██   █▌▓██ ░▄█ ▒▒██░  ██▒▒██▒░██   █▌   \e[0m'
	echo -e $'\e[1;33m\e[0m\e[1;37m       ▒   ██▒▓▓█  ░██░░▓█▄   ▌▒██▀▀█▄  ▒██   ██░░██░░▓█▄   ▌   \e[0m'
	echo -e $'\e[1;33m\e[0m\e[1;37m     ▒██████▒▒▒▒█████▓ ░▒████▓ ░██▓ ▒██▒░ ████▓▒░░██░░▒████▓    \e[0m'
	echo -e $'\e[1;33m\e[0m\e[1;37m     ▒ ▒▓▒ ▒ ░░▒▓▒ ▒ ▒  ▒▒▓  ▒ ░ ▒▓ ░▒▓░░ ▒░▒░▒░ ░▓   ▒▒▓  ▒    \e[0m'
	echo -e $'\e[1;33m\e[0m\e[1;37m     ░ ░▒  ░ ░░░▒░ ░ ░  ░ ▒  ▒   ░▒ ░ ▒░  ░ ▒ ▒░  ▒ ░ ░ ▒  ▒    \e[0m'
	echo -e $'\e[1;33m\e[0m\e[1;37m     ░  ░  ░   ░░░ ░ ░  ░ ░  ░   ░░   ░ ░ ░ ░ ▒   ▒ ░ ░ ░  ░    \e[0m'
	echo -e $'\e[1;33m\e[0m\e[1;37m           ░     ░        ░       ░         ░ ░   ░     ░       \e[0m'
	echo -e $'\e[1;33m\e[0m\e[1;37m                          ░                             ░       \e[0m'
	
	
	echo""    
	echo -e $'\e[1;33m\e[0m\e[1;33m    ██████████\e[0m'"\e[96m██████████"'\e[1;33m\e[0m\e[1;31m██████████\e[0m' '\e[1;32m\e[0m\e[1;32m grant root privileges on your android device with sudroid \e[0m''\e[1;37m\e[0m\e[1;37m \e[0m'                                       
	echo ""
	echo -e $'\e[1;33m\e[0m\e[1;33m  [ \e[0m\e[1;32m Follow on Github :- https://github.com/54R4T1KY4N \e[0m \e[1;32m\e[0m\e[1;33m] \e[0m'
	echo ""
	echo -e $'\e[1;37m\e[0m\e[1;37m    +-+-+-+-+-+-+-+ >>\e[0m'
	echo -e "\e[93m    suDROID |3|.|2| stable"      
	echo -e $'\e[1;37m\e[0m\e[1;37m    +-+-+-+-+-+-+-+ >>\e[0m' 
	echo ""                                                
}
banner 

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

            
banner1 "now we are checking the Linux distribution and installing the necessary packages"
            

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
    banner1 "Unsupported Linux distribution"
    exit 1
fi

# Check for adb and fastboot installation
banner1 "checking if adb and fastboot installed"
if ! command -v adb &> /dev/null || ! command -v fastboot &> /dev/null; then
    banner1 "adb and fastboot not found. Please make sure they are installed and added to your PATH."
    exit 1
fi

# Connect Android device via USB and check if it's connected
banner1 "Please connect your Android device via USB and make sure USB debugging is enabled."
            
sleep 45
adb wait-for-device
if [ $? -eq 0 ]; then
  banner1 "Device connected successfully"
              
else
  banner1 "Device not connected. Please make sure that the USB cable and the device port is working and USB debugging is enabled."
              
  exit 1
fi

# Enable developer options on the Android device
banner1 "Enabling developer options..."
            
adb shell settings put global development_settings_enabled 1 > /dev/null 2>&1
sleep 20

# Enable USB debugging on the Android device
banner1 "Checking and (if needed) Enabling the USB debugging..."
            
adb shell settings put global adb_enabled 1 > /dev/null 2>&1
sleep 20

# Reboot the Android device into bootloader mode
banner1 "Rebooting into bootloader mode..."
            
adb reboot bootloader > /dev/null 2>&1
sleep 90

# Download and install Magisk
   banner1 "Downloading Magisk..."
               
    wget https://github.com/topjohnwu/Magisk/releases/download/v23.0/Magisk-v23.0.zip -O magisk.zip > /dev/null 2>&1
    sleep 20
    banner1 "Installing Magisk..."
                
    unzip -j magisk.zip -d magisk > /dev/null 2>&1
    sleep 20
    rm magisk.zip
   

# Export the boot.img from the connected Android device
banner1 "Exporting boot.img from the connected Android device..."
     
banner1 "Check if boot.img file exists in any possible directory"

# Search for boot.img file on the device
boot_img_path="$(adb shell find / -name 'boot.img' 2>/dev/null | tr -d '\r')"
if [ -z "$boot_img_path" ]; then
  banner1 "Could not find boot.img file on the device."
  exit 1
fi

# Export boot.img file to working directory
banner1 "Exporting boot.img from device..."
adb pull "$boot_img_path" >/dev/null 2>&1
if [ $? -ne 0 ]; then
  banner1 "Failed to export boot.img. Please provide the path to your boot.img file: "
  read boot_img_path
else
  banner1 "boot.img exported successfully."
  boot_img_path="./boot.img"
  
  banner1 "Backup proccess for the the boot.img was started, so you can roll-back if something shittttyyy happaned"
  mkdir -p ../"backup_$(date +"%Y%m%d")" && cp ./boot.img ../"backup_$(date +"%Y%m%d")"/boot.img.bak
  
fi

# Patch boot.img with Magisk
banner1 "Patching boot.img with Magisk..."
magisk --version >/dev/null 2>&1
if [ $? -eq 0 ]; then
chmod +x magisk*
  magisk --boot-image "$boot_img_path" "patched_boot.img" >/dev/null 2>&1
else
  banner1 "Magisk not found. Please download and install it manually from https://github.com/topjohnwu/Magisk/releases."
  exit 1
fi


# If boot.img is not found, prompt the user to provide it
if [ -z "$boot_img_path" ]; then
  read -p "Please provide the path to your boot.img file: " boot_img_path
fi

# Reboot device into fastboot mode
banner1 "Rebooting device into fastboot mode..."
adb reboot bootloader >/dev/null 2>&1

# Flash patched boot.img to device
banner1 "Flashing patched boot.img to device..."
fastboot flash boot "patched_boot.img" >/dev/null 2>&1
sleep 20

# Reboot device
banner1 "Rebooting device..."
fastboot reboot >/dev/null 2>&1

# Clean up the downloaded files
banner1 "Cleaning up..."
            
rm magisk.zip
cd .. && rm -rf patching_process

# Clean up installed packages
if [[ -n "${cleanup_cmd}" ]]; then
    echo "Removing installed packages..."
    ${cleanup_cmd}
fi

banner1 "Done!"
banner1 "If you have any problems contact with me"
banner1 "Also you can always recover from your original boot.img that is located in the backup directory (named as boot.img.bak)"
