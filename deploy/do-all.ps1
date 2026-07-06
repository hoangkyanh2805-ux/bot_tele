# Chay het: tao script VPS, thu SSH deploy, tat bot local
$ErrorActionPreference = "Continue"
$ProjectRoot = Split-Path $PSScriptRoot -Parent
$VpsIp = "103.97.126.28"
$SshPort = 2018
$PasteFile = Join-Path $PSScriptRoot "vps-paste.sh"

Write-Host "=== 1/4 Tao script cai dat VPS ===" -ForegroundColor Cyan
& (Join-Path $PSScriptRoot "generate-vps-script.ps1") -ProjectRoot $ProjectRoot -OutputFile $PasteFile

Write-Host ""
Write-Host "=== 2/4 Thu deploy qua SSH ===" -ForegroundColor Cyan
$sshTest = ssh -p $SshPort -o BatchMode=yes -o ConnectTimeout=12 "root@${VpsIp}" "echo SSH_OK" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "SSH OK - dang upload va cai dat..."
    scp -P $SshPort $PasteFile "root@${VpsIp}:/tmp/vps-paste.sh"
    ssh -p $SshPort "root@${VpsIp}" "bash /tmp/vps-paste.sh && rm -f /tmp/vps-paste.sh"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Deploy VPS thanh cong!" -ForegroundColor Green
        $deployed = $true
    }
} else {
    Write-Host "SSH khong ket noi duoc: $sshTest" -ForegroundColor Yellow
    $deployed = $false
}

Write-Host ""
Write-Host "=== 3/4 Tat bot Telegram tren may Windows ===" -ForegroundColor Cyan
Get-CimInstance Win32_Process -Filter "name='python.exe'" | ForEach-Object {
    if ($_.CommandLine -like "*Bot_Tele*bot.py*") {
        Write-Host "Dung process $($_.ProcessId): Bot_Tele"
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

Write-Host ""
Write-Host "=== 4/4 Ket qua ===" -ForegroundColor Cyan
if ($deployed) {
    Write-Host "Bot da chay tren VPS. Kiem tra: ssh -p $SshPort root@$VpsIp 'journalctl -u bot-tele -n 20'" -ForegroundColor Green
} else {
    Write-Host "Chua deploy duoc tu may nay. Lam buoc cuoi bang VNC Console 123host:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "1. Mo VNC Console tren panel 123host"
    Write-Host "2. Dang nhap root"
    Write-Host "3. Paste lenh sau (copy tu file):"
    Write-Host "   $PasteFile"
    Write-Host ""
    Write-Host "Hoac chay tren VPS:"
    Write-Host "   bash <(curl -fsSL file...)  -- KHONG dung cach nay vi can file local"
    Write-Host ""
    Write-Host "Cach nhanh: mo file vps-paste.sh, copy TOAN BO, paste vao VNC."
    try {
        Get-Content $PasteFile -Raw | Set-Clipboard
        Write-Host "Da copy script vao clipboard!" -ForegroundColor Green
    } catch {
        Write-Host "Khong copy clipboard duoc - mo file thu cong."
    }
}
