	    ██████  █    ██ ▓█████▄  ██▀███   ▒█████   ██▓▓█████▄   
	  ▒██    ▒  ██  ▓██▒▒██▀ ██▌▓██ ▒ ██▒▒██▒  ██▒▓██▒▒██▀ ██▌  
	  ░ ▓██▄   ▓██  ▒██░░██   █▌▓██ ░▄█ ▒▒██░  ██▒▒██▒░██   █▌  
	    ▒   ██▒▓▓█  ░██░░▓█▄   ▌▒██▀▀█▄  ▒██   ██░░██░░▓█▄   ▌  
	  ▒██████▒▒▒▒█████▓ ░▒████▓ ░██▓ ▒██▒░ ████▓▒░░██░░▒████▓   
	  ▒ ▒▓▒ ▒ ░░▒▓▒ ▒ ▒  ▒▒▓  ▒ ░ ▒▓ ░▒▓░░ ▒░▒░▒░ ░▓   ▒▒▓  ▒   
	  ░ ░▒  ░ ░░░▒░ ░ ░  ░ ▒  ▒   ░▒ ░ ▒░  ░ ▒ ▒░  ▒ ░ ░ ▒  ▒   
	  ░  ░  ░   ░░░ ░ ░  ░ ░  ░   ░░   ░ ░ ░ ░ ▒   ▒ ░ ░ ░  ░   
	        ░     ░        ░       ░         ░ ░   ░     ░      
	                       ░                             ░      

# suDROID
This script provides a convenient and automated way to patch the boot image of an Android device, saving your time and effort compared to manually patching the image.


The script performs the following steps:

• It checks if the required tools, such as adb and fastboot, are installed on the system. If any tool is missing, the script prompts the user to install it.
• The script prompts the user to connect the Android device to the computer via USB and ensure that USB debugging is enabled on the device.
• The script then reboots the device into bootloader mode using adb.
• It extracts the boot image from the device using adb.
• The script applies a set of patches to the boot image using the patch tool. These patches include disabling dm-verity, disabling forced encryption, and enabling insecure adb.
• The patched boot image is then flashed back to the device using fastboot.
• The device is then rebooted into the system, and the script terminates.

HOW TO USE

1. Open a terminal window in Linux.
2. Download (git clone) this repo
3. Navigate to the repo directory
4. Plug your Android device via USB cable
5. Take a cup of coffee, tee maybe beer or wine (why not)
6. Run the script as sudo (sudo ./sudroid.sh)
7. Relax until you get the Done! message.
8. Unplug your Android device
9. Enjoy



ONE MORE NOTE!!!!!

use this script at your own risk
i'm not responsible for the sh*t that happened
