$ProjectRoot = $PSScriptRoot
$PidFile = Join-Path $ProjectRoot ".bot.pid"

if (Test-Path $PidFile) {
    $botPid = [int](Get-Content $PidFile -Raw)
    Stop-Process -Id $botPid -Force -ErrorAction SilentlyContinue
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
}

Get-CimInstance Win32_Process -Filter "name='python.exe'" | ForEach-Object {
    $cmd = $_.CommandLine
    if ($cmd -match 'bot\.py' -and ($cmd -match 'hermes-agent' -or $cmd -match 'Bot_Tele')) {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "Da dung bot local."
