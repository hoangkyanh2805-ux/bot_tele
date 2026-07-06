$ProjectRoot = $PSScriptRoot
$PidFile = Join-Path $ProjectRoot ".bot.pid"
$LogFile = Join-Path $ProjectRoot "bot.log"

Set-Location -LiteralPath $ProjectRoot

# Dung instance cu (hermes-agent hoac lan chay truoc)
& (Join-Path $ProjectRoot "stop-bot.ps1") | Out-Null

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Tao virtualenv..."
    python -m venv .venv
    & .\.venv\Scripts\pip.exe install -r requirements.txt
}

$python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$proc = Start-Process -FilePath $python -ArgumentList "bot.py" -WorkingDirectory $ProjectRoot `
    -WindowStyle Hidden -RedirectStandardOutput $LogFile -RedirectStandardError "${LogFile}.err" -PassThru

$proc.Id | Set-Content -Path $PidFile -Encoding ascii
Write-Host "Bot da chay (PID $($proc.Id)). Log: $LogFile"
Start-Sleep -Seconds 3
Get-Content $LogFile -Tail 5 -ErrorAction SilentlyContinue
