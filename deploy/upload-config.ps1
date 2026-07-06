# Upload .env va mappings.json len VPS
# Chay: .\deploy\upload-config.ps1

$VpsIp = "103.97.126.28"
$SshPort = 2018
$User = "root"
$RemoteDir = "/opt/bot_tele"
$ProjectRoot = Split-Path $PSScriptRoot -Parent

$EnvFile = Join-Path $ProjectRoot ".env"
$MappingsFile = Join-Path $ProjectRoot "mappings.json"

if (-not (Test-Path $EnvFile)) {
    Write-Error "Khong tim thay .env tai: $EnvFile"
    exit 1
}
if (-not (Test-Path $MappingsFile)) {
    Write-Error "Khong tim thay mappings.json tai: $MappingsFile"
    exit 1
}

Write-Host "Upload .env va mappings.json -> ${User}@${VpsIp}:${RemoteDir}"
scp -P $SshPort $EnvFile "${User}@${VpsIp}:${RemoteDir}/.env"
scp -P $SshPort $MappingsFile "${User}@${VpsIp}:${RemoteDir}/mappings.json"

Write-Host "Restart bot tren VPS..."
ssh -p $SshPort "${User}@${VpsIp}" "systemctl restart bot-tele && systemctl status bot-tele --no-pager"

Write-Host "Xong."
