# Copy this project onto the Raspberry Pi 4B.
# Usage (PowerShell, this PC):
#   .\scripts\copy-to-pi.ps1
#   .\scripts\copy-to-pi.ps1 pi@192.168.1.50

param(
    [string]$Pi = "pi@raspberrypi.local"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Write-Host "Creating ~/billiard-stroke on $Pi ..."
ssh $Pi "mkdir -p ~/billiard-stroke"

Write-Host "Copying files..."
scp -r `
    "$root\main.py" `
    "$root\config.py" `
    "$root\requirements.txt" `
    "$root\stroke_sim" `
    "$root\scripts" `
    "${Pi}:~/billiard-stroke/"

Write-Host "On the Pi, run:"
Write-Host "  cd ~/billiard-stroke"
Write-Host "  chmod +x scripts/setup-pi.sh"
Write-Host "  ./scripts/setup-pi.sh"
