	                                       
	         ____  _____ _____ _____ ____  
	 ___ _ _|    \| __  |     |     |    \ 
	|_ -| | |  |  |    -|  |  |-   -|  |  |
	|___|___|____/|__|__|_____|_____|____/ 
                                       
# suDROID v2.0

🌌 suDROID

suDROID is a cross-platform solution designed to streamline the rooting process for Android devices on both Linux and Windows. With easy-to-follow instructions and automated tasks, suDROID empowers users to unlock advanced Android capabilities with confidence.

	Warning: Rooting can be risky! Be sure to understand the implications before proceeding, 
 		 and always have a backup of your important data.

📄 Changelog and Release Notes
Version 2.1.1 - October 31, 2024
🔥 Major Features and Enhancements

    Dynamic Device Detection and Compatibility Check
        Automatically detects device model and Android version for compatibility verification. Provides specific guidance for supported models (e.g., Google Pixel, Samsung Galaxy, OnePlus).

    Automatic Magisk Version Update
        Fetches the latest Magisk version dynamically from the GitHub API, ensuring you’re always up-to-date with the latest release. Configurable fallback to a default version if updates are not available.

    Interactive Mode for Customizable Rooting Steps
        New interactive menu allows users to select each stage of the rooting process individually. This makes it possible to skip, repeat, or inspect each step at your convenience.

    Automatic Bootloader Unlock
        Detects if the bootloader is locked and, if so, attempts to unlock it automatically. If the unlock attempt fails, the script provides detailed manual instructions.

    Full Device and Settings Backup
        Allows a comprehensive backup of all user data (apps, settings, media) and system settings to a secure backup directory before starting the rooting process. Restores settings seamlessly after rooting to preserve your device's original configuration.

    Advanced Root Verification
        Conducts an extensive root verification, checking for the su binary and other root files. Confirms root access by executing root-level commands and reports if rooting was successful.

    Retry Mechanisms for Stability
        Adds a retry mechanism for critical tasks such as internet connectivity checks, battery level checks, ADB/fastboot operations, and file downloads. Ensures stability in cases of intermittent network or device connection issues.

    Custom Config File Support
        Includes a configuration file (root_config.cfg) that allows users to pre-define settings such as Magisk version, retry limits, and verbosity, making the script customizable for both advanced and basic users.

    Safety Mode with Rollback Options
        Introduces a Safety Mode that backs up critical files at each step, allowing for a quick rollback in the event of errors during the rooting process.

    Post-Root Recovery Options
        Offers the option to install a custom recovery (e.g., TWRP) after rooting, providing advanced device management tools for rooted devices.

📈 Optimizations and Improvements

    Streamlined Setup and Dependency Management
        Enhanced compatibility for Linux distributions (Debian, Fedora, Arch, OpenSUSE). Automatically detects and installs necessary dependencies, streamlining the setup for each environment.

    Enhanced Logging and Detailed Error Reporting
        Logs are now enriched with timestamped error messages and troubleshooting suggestions for each critical failure point. Logs device state information, making it easy to track down issues and ensure a smooth rooting process.

    Improved Interactive Prompts and User Guidance
        Updated prompts with color-coded messages and step-by-step instructions, guiding users through the rooting process and offering a preview of each action before execution.

    Automatic Cleanup and Organization
        Cleans up temporary files and directories upon completion, organizing backups and logs into designated folders for easier management and faster access.

🛠️ Bug Fixes

    Resolved ADB and Fastboot Detection Issues
        Ensures consistent detection and accessibility of ADB and Fastboot binaries, improving reliability across various Linux environments.

    Fixed Battery Level Detection for Low-Level Devices
        Enhanced battery detection mechanism to handle edge cases on low-battery or low-power devices, ensuring sufficient power for the rooting process.

📝 How to Use

    Clone or Download the Repository
        Ensure you have adb, fastboot, curl, wget, unzip, and jq installed. Use ./root_config.cfg to set up preferred configurations.

    Run the Script
        Start with bash root_script.sh and follow the interactive menu to proceed with the rooting steps. Choose steps individually or proceed with a complete automated run.

    Backup Data and Settings
        It’s recommended to use the built-in backup feature before rooting to ensure data is safe and recoverable.

    Post-Root Options
        After verifying root access, the script offers the option to install custom recovery (e.g., TWRP) for advanced system management.

⚠️ Important Notes

    Device Compatibility: The script has been tested on Pixel, Samsung Galaxy, Xiaomi, Nokia, Sony Xperia, LG and OnePlus devices. For unsupported devices, the script provides general instructions but may require manual adjustments.
    
    The script has been tested and optimized for the following devices:

    Google Pixel Series
        Pixel 4a
        Pixel 5
        Pixel 6
        Pixel 6 Pro

    Samsung Galaxy Series
        Galaxy S10
        Galaxy S20
	Galaxy Note 10 and Note 20
        Galaxy S21
	Galaxy S22
 	Galaxy S23
  	Galaxy S24
 	(Exynos versions recommended due to compatibility with bootloader unlocking)

    OnePlus Series
        OnePlus 6, 6T
        OnePlus 7, 7 Pro
        OnePlus 8, 8 Pro
        OnePlus 9, 9 Pro

    Xiaomi Mi Series
        Mi 9
        Mi 10
        Mi 11
	
    Xiaomi Series
        13
        14

    Other Devices
        Sony Xperia (Xperia XZ2, Xperia XZ3)
        Motorola (Moto G7, Moto G8)
        LG (G7 ThinQ, V40 ThinQ)
	
    Battery Requirements: Ensure your device is charged to at least 50% before beginning the process.
    Rooting Disclaimer: Rooting may void your device warranty. Ensure you fully understand the risks involved.

🚀 Ready to Root?

This version is built for flexibility, security, and stability, offering a fully automated yet customizable rooting experience for advanced users and beginners alike. Get started, and unlock the full potential of your Android device!

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
   
	chmod +x suDROID2.1.sh
	./suDROID2.1.sh

On Windows:
   
	Open PowerShell as Administrator.
	Navigate to the script’s directory.
	Run the script:
	.\suDROID.ps1

Follow the Prompts

The script will guide you through each step, including enabling USB debugging, checking bootloader status, and flashing the patched boot image with Magisk.

📜 Script Details

Linux (Bash) Script: suDROID2.1.sh

The Bash script automates the rooting process for Linux users, using common Linux package managers to install dependencies, check device connectivity, retrieve and patch the boot image, and flash it back onto the device.

Windows (PowerShell) Script: suDROID.ps1

The PowerShell script provides a smooth rooting experience for Windows users by utilizing native commands for dependency management, file handling, and boot image patching with Magisk.

⚠️ Disclaimer

Rooting your device may void its warranty, cause data loss, or result in unintended behavior. suDROID is provided “as-is” without warranty. Proceed at your own risk and ensure you understand each step before executing the script.

ChatGPT
🚀 Planned Future Updates

To enhance the functionality, compatibility, and user experience of the rooting script, the following updates are being planned:
🔧 Extended Device Compatibility

    Expanded Device Support: Broaden compatibility for additional manufacturers and models, especially newer devices from brands like Google, Samsung, Xiaomi, Motorola, and OnePlus.
    Amazon Fire (just think anout it)
    Automated Device Profiles: Add device-specific profiles to streamline the rooting process based on detected model and firmware. This will offer device-tailored instructions, especially for Samsung and Xiaomi devices where rooting methods vary.

📦 Comprehensive Backup and Restore Enhancements

    Selective Backup Options: Provide options for partial backups, such as only apps, media files, or system settings. Users will be able to select which data to back up and restore.
    Cloud Backup Support: Integrate options for uploading backups to cloud services (e.g., Google Drive) for safe storage and easy retrieval.

🌐 Device Information and Diagnostic Tools

    Detailed System Info Report: Generate a complete system report (including CPU, GPU, memory, storage, and current firmware) to assess compatibility.
    Real-Time Diagnostics: Implement real-time monitoring of battery, CPU temperature, and system performance during the rooting process to prevent overheating or sudden shutdowns.

🔒 Enhanced Security and Safety Features

    Automatic Safety Mode: Introduce a Safety Mode that checks essential conditions (battery level, bootloader status, backup completion) before initiating the root process. If any condition fails, the process will halt automatically.
    Encryption Check: Identify if the device’s data partition is encrypted and notify the user if decryption is needed, preventing issues during or after rooting.

🔄 Automated Root Recovery and Troubleshooting

    Root Recovery Mode: Add a Root Recovery Mode that re-applies root access if it becomes lost or broken after a system update.
    Enhanced Error Logging: Expand error logging to include specific troubleshooting suggestions based on common failure points, making it easier for users to resolve issues.

🧩 Custom Recovery Installation and Management

    TWRP Installation Option: Provide an option to automatically install the latest compatible version of TWRP or other custom recoveries based on the detected device model.
    Recovery Mode Features: Add options for custom backups, system wipes, and advanced recovery tools within the TWRP environment.

⚙️ User Interface and Experience Enhancements

    Guided Setup Wizard: Include a setup wizard that walks users through configuring key options, such as backup preferences, root verification, and Safety Mode settings.
    GUI Version: Develop a basic GUI interface for Linux (using Zenity or similar tools) to simplify the rooting process, making it accessible for non-technical users.

🆕 Additional Root Utilities and Tools

    Post-Root Utility Installations: Offer optional installations of popular root utilities like BusyBox, terminal emulators, and root file explorers.
    System Tweaks and Performance Optimization: Provide options to apply common performance tweaks, such as adjusting CPU governors, disabling system bloatware, or optimizing battery management.

📜 License

This project is licensed under the MIT License. See the LICENSE file for details.

I welcome contributions and feedback to enhance suDROID and improve the Android rooting experience across platforms.
