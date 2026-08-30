#!/bin/bash
# Run on the Raspberry Pi 4B, from the project folder.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "Enabling I2C..."
sudo raspi-config nonint do_i2c 0

echo "Installing system packages..."
sudo apt-get update
sudo apt-get install -y \
  python3-pip python3-venv python3-dev python3-pil \
  python3-pigpio pigpio pigpio-tools i2c-tools

echo "Starting pigpio..."
sudo systemctl enable pigpiod
sudo systemctl start pigpiod || sudo pigpiod || true

echo "Python venv..."
python3 -m venv --system-site-packages .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt

echo
echo "I2C devices (OLED often 3c, ADS1115 often 48):"
sudo i2cdetect -y 1 || true
echo
echo "Setup done. Next:"
echo "  source .venv/bin/activate"
echo "  python3 main.py --mode oled"
echo "  python3 main.py --mode encoder"
echo "  python3 main.py --mode jog"
echo "  python3 main.py"
