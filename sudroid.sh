#!/bin/bash

banner1()
{
  echo "+---------------------------------------------------------------------------------------------+"
  printf "| %-40s |\n" "`date`"
  echo "|                                                                                             |"
  printf "|`tput bold` %-40s `tput sgr0`|\n" "$@"
  echo "+---------------------------------------------------------------------------------------------+"
}

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



# Create a new directory called "runing_dir"
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
            
adb wait-for-device
adb shell su -c 'dd if=/dev/block/bootdevice/by-name/boot of=/sdcard/boot.img'
adb pull /sdcard/boot.img boot.img.bak
mkdir -p ../"backup_$(date +"%Y%m%d")" && cp ./boot.img.bak ../"backup_$(date +"%Y%m%d")"/boot.img.bak
banner1 "Backup of original boot.img created as boot.img.bak"
            

# Patch boot.img with Magisk
mv magisk*.img magisk.img && chmod +x magisk.img
./magisk --patch ../boot.img.bak
sleep 45

# Reboot the Android device into bootloader mode
banner1 "Rebooting into bootloader mode..."
            
adb reboot bootloader > /dev/null 2>&1
sleep 90

# Flash the patched boot image back to the Android device
banner1 "Copying the patched boot image back to the Android device..."
            
# Flash patched boot.img to Android device
fastboot flash boot magisk_patched.img
sleep 90

# Reboot the Android device
banner1 "Rebooting device..."
            
fastboot reboot > /dev/null 2>&1

# Clean up the downloaded files
banner1 "Cleaning up..."
            
rm magisk.zip
cd .. && rm -rf patching_process

banner1 "Done! If you have any problems contact with me, also you can always recover from your original boot.img that is located in the backup directory."
            


