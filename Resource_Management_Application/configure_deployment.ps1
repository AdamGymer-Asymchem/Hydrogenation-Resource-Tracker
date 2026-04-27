param(
    [string]$DbPath = "",
    [int]$Port = 17001,
    [string]$PortalPassword = "LotsOfBubbles",
    [string]$HostName = "0.0.0.0"
)

$ErrorActionPreference = "Stop"
$appRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

if ([string]::IsNullOrWhiteSpace($DbPath)) {
    $DbPath = Join-Path $appRoot "requests.db"
}

$resolvedDbPath = [System.IO.Path]::GetFullPath($DbPath)
$dbDirectory = Split-Path -Parent $resolvedDbPath
if (-not (Test-Path -LiteralPath $dbDirectory)) {
    New-Item -ItemType Directory -Path $dbDirectory | Out-Null
}

$envPath = Join-Path $appRoot "deployment.env"
$content = @(
    "# Hydrogenation Resource Tracker deployment configuration"
    "RESOURCE_TRACKER_DB_PATH=$resolvedDbPath"
    "PORT=$Port"
    "HOST=$HostName"
    "PORTAL_PASSWORD=$PortalPassword"
)

Set-Content -Path $envPath -Value $content -Encoding ASCII

Write-Host "Wrote deployment configuration to $envPath"
Write-Host "Database path: $resolvedDbPath"
Write-Host "Port: $Port"
Write-Host "Portal password: $PortalPassword"
