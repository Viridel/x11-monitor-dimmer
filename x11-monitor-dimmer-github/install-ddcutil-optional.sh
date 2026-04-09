#!/bin/bash
set -e

echo "X11 Monitor Dimmer — Optional ddcutil Installer"
echo
echo "This helper is intentionally optional."
echo
echo "Purpose:"
echo "  This script only checks whether ddcutil is installed, and offers"
echo "  to install it if it is missing."
echo
echo "Current intended use in this project:"
echo "  - read-only display identification"
echo "  - EDID/model-name retrieval"
echo "  - optional future hardware probing"
echo
echo "This script does NOT:"
echo "  - modify the dimmer configuration"
echo "  - change any monitor names already saved in the app"
echo "  - enable hardware brightness control"
echo "  - apply driver tweaks or DDC permission fixes"
echo
echo "Helpful references:"
echo "  - ddcutil I2C permissions:"
echo "    https://www.ddcutil.com/i2c_permissions/"
echo "  - ArchWiki display control / DDC/CI:"
echo "    https://wiki.archlinux.org/title/Display_control"
echo
if command -v ddcutil >/dev/null 2>&1; then
    echo "ddcutil is already installed."
    echo "No changes will be made."
    echo
    echo "Executable path:"
    command -v ddcutil
    echo
    echo "Detected version:"
    ddcutil --version | head -n 1
    exit 0
fi

echo "ddcutil is not currently installed."
echo
echo "If you continue, this script will run:"
echo "  sudo apt update"
echo "  sudo apt install -y ddcutil"
echo
echo "This may prompt for your password."
echo "No other changes will be made."
echo

read -r -p "Proceed with optional ddcutil installation? [Y/N] " reply

case "$reply" in
    y|Y|yes|YES)
        echo
        echo "Updating package lists..."
        sudo apt update
        echo
        echo "Installing ddcutil..."
        sudo apt install -y ddcutil
        echo
        echo "ddcutil installation complete."
        echo
        echo "Installed version:"
        ddcutil --version | head -n 1
        ;;
    *)
        echo
        echo "Optional ddcutil installation skipped."
        exit 0
        ;;
esac
