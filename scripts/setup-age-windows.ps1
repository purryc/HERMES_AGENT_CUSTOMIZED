param(
    [string]$Label = "windows-hermes-codex"
)

$ErrorActionPreference = "Stop"

$workspaceRoot = "F:\AGENT"
$distro = "Ubuntu-24.04"
wsl.exe -d $distro -- bash -lc "chmod +x /mnt/f/AGENT/scripts/setup-age-wsl.sh && /mnt/f/AGENT/scripts/setup-age-wsl.sh '$Label'"

Write-Host "age is ready."
Write-Host "Private identity: $workspaceRoot\.secrets\age\$Label.identity.txt"
Write-Host "Public recipient: $workspaceRoot\keys\$Label.recipient.txt"
Write-Host "Recipients list: $workspaceRoot\keys\recipients.txt"
Write-Host "Back up the private identity somewhere safe. Do not commit it."
