#!/bin/bash
# Hoan tat cai dat sau khi pip install xong
set -euo pipefail

APP_DIR="/opt/bot_tele"
SERVICE_NAME="bot-tele"

cd "$APP_DIR"

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "!!! Chua co .env - chay: nano .env (dien token + ADMIN_IDS)"
  echo "    Sau do chay lai: bash deploy/finish-vps.sh"
  exit 1
fi

if grep -q "thay_token_botfather_vao_day" .env; then
  echo "!!! .env chua co token that - chay: nano .env"
  exit 1
fi

if [ ! -f "mappings.json" ]; then
  cp mappings.example.json mappings.json
  echo "Da tao mappings.json mau - sua bang /map tren Telegram neu can."
fi

cat > "/etc/systemd/system/${SERVICE_NAME}.service" << EOF
[Unit]
Description=Telegram Relay Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${APP_DIR}
ExecStart=${APP_DIR}/.venv/bin/python bot.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"
sleep 2
systemctl status "$SERVICE_NAME" --no-pager
echo ""
echo "=== XONG ==="
