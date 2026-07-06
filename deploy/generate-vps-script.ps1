# Tao script cai dat 1 lan cho VPS (paste vao VNC Console)
param(
    [string]$ProjectRoot = (Split-Path $PSScriptRoot -Parent),
    [string]$OutputFile = (Join-Path $PSScriptRoot "vps-paste.sh")
)

$EnvFile = Join-Path $ProjectRoot ".env"
$MappingsFile = Join-Path $ProjectRoot "mappings.json"

if (-not (Test-Path $EnvFile)) { throw "Thieu .env: $EnvFile" }
if (-not (Test-Path $MappingsFile)) { throw "Thieu mappings.json: $MappingsFile" }

$envB64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes((Get-Content $EnvFile -Raw -Encoding UTF8)))
$mapB64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes((Get-Content $MappingsFile -Raw -Encoding UTF8)))

$script = @"
#!/bin/bash
set -euo pipefail

APP_DIR="/opt/bot_tele"
REPO_URL="https://github.com/hoangkyanh2805-ux/bot_tele.git"
SERVICE_NAME="bot-tele"

echo "=== Cai Telegram Relay Bot ==="

dnf install -y python3 python3-pip git curl

if [ -d "`$APP_DIR/.git" ]; then
  git -C "`$APP_DIR" pull --ff-only
else
  git clone "`$REPO_URL" "`$APP_DIR"
fi

cd "`$APP_DIR"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "$envB64" | base64 -d > .env
echo "$mapB64" | base64 -d > mappings.json
chmod 600 .env mappings.json

cat > /etc/systemd/system/`${SERVICE_NAME}.service << 'SVCEOF'
[Unit]
Description=Telegram Relay Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/bot_tele
ExecStart=/opt/bot_tele/.venv/bin/python bot.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable "`$SERVICE_NAME"
systemctl restart "`$SERVICE_NAME"
sleep 2
systemctl status "`$SERVICE_NAME" --no-pager
echo ""
echo "=== XONG ==="
echo "Log: journalctl -u bot-tele -f"
"@

[System.IO.File]::WriteAllText($OutputFile, $script, [Text.UTF8Encoding]::new($false))
Write-Host "Da tao: $OutputFile"
