param(
    [string]$Port = "COM3",
    [int]$Baud = 115200
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$buildDir = Join-Path $root "firmware\m5sticks3_pet\.pio\build\m5sticks3_pet"
$bootloader = Join-Path $buildDir "bootloader.bin"
$partitions = Join-Path $buildDir "partitions.bin"
$firmware = Join-Path $buildDir "firmware.bin"
$bootApp0 = Join-Path $env:USERPROFILE ".platformio\packages\framework-arduinoespressif32\tools\partitions\boot_app0.bin"

$requiredFiles = @($bootloader, $partitions, $firmware, $bootApp0)
foreach ($file in $requiredFiles) {
    if (-not (Test-Path $file)) {
        throw "Missing required file: $file"
    }
}

Write-Host "Put the CoreS3 into download mode first:" -ForegroundColor Cyan
Write-Host "1. Long press RESET for about 2 seconds until the green LED lights up." -ForegroundColor Cyan
Write-Host "2. Release RESET, then press Enter here to start flashing." -ForegroundColor Cyan
[void](Read-Host)

$args = @(
    "-m", "esptool",
    "--chip", "esp32s3",
    "--port", $Port,
    "--baud", $Baud,
    "--before", "no-reset",
    "--after", "watchdog-reset",
    "write-flash",
    "0x0", $bootloader,
    "0x8000", $partitions,
    "0xE000", $bootApp0,
    "0x10000", $firmware
)

Write-Host "Flashing $Port ..." -ForegroundColor Green
& py @args

if ($LASTEXITCODE -ne 0) {
    throw "Flashing failed with exit code $LASTEXITCODE"
}

Write-Host "Flash completed." -ForegroundColor Green
