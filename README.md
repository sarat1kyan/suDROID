	                                       
	         ____  _____ _____ _____ ____  
	 ___ _ _|    \| __  |     |     |    \ 
	|_ -| | |  |  |    -|  |  |-   -|  |  |
	|___|___|____/|__|__|_____|_____|____/ 
                                       
# suDROID v2.0

🌌 suDROID

suDROID is a cross-platform solution designed to streamline the rooting process for Android devices on both Linux and Windows. With easy-to-follow instructions and automated tasks, suDROID empowers users to unlock advanced Android capabilities with confidence.

	Warning: Rooting can be risky! Be sure to understand the implications before proceeding, 
 		 and always have a backup of your important data.

🚀 Features

	•	Cross-Platform Support: Compatible with both Linux (Bash) and Windows (PowerShell).
	•	Automated Workflow: From dependency installation to device connection, boot image patching, and flashing, suDROID covers the entire rooting process.
	•	User-Friendly Prompts: Interactive prompts and informative error messages make the process straightforward.
	•	Logs & Backups: Automatic creation of logs and a backup of the original boot image for safety.

🛠 Requirements

Before you begin, make sure you have:

	1.	ADB (Android Debug Bridge) and Fastboot installed and accessible in your system’s PATH. (Script will perform the necessary checks by itself)
	2.	USB Debugging and OEM Unlocking enabled on your Android device (usually found in Developer Options).

🔧 Getting Started

Clone the Repository

	git clone https://github.com/yourusername/suDROID.git
	cd suDROID

Run the Script

On Linux:
   
	chmod +x suDROID.sh
	./suDROID.sh

On Windows:
   
	Open PowerShell as Administrator.
	Navigate to the script’s directory.
	Run the script:
	.\suDROID.ps1

Follow the Prompts

The script will guide you through each step, including enabling USB debugging, checking bootloader status, and flashing the patched boot image with Magisk.

📜 Script Details

Linux (Bash) Script: suDROID.sh

The Bash script automates the rooting process for Linux users, using common Linux package managers to install dependencies, check device connectivity, retrieve and patch the boot image, and flash it back onto the device.

Windows (PowerShell) Script: suDROID.ps1

The PowerShell script provides a smooth rooting experience for Windows users by utilizing native commands for dependency management, file handling, and boot image patching with Magisk.

⚠️ Disclaimer

Rooting your device may void its warranty, cause data loss, or result in unintended behavior. suDROID is provided “as-is” without warranty. Proceed at your own risk and ensure you understand each step before executing the script.

📜 License

This project is licensed under the MIT License. See the LICENSE file for details.

I welcome contributions and feedback to enhance suDROID and improve the Android rooting experience across platforms.
