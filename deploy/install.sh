#!/bin/bash
set -euo pipefail

APP_DIR="/opt/bot_tele"
REPO_URL="https://github.com/hoangkyanh2805-ux/bot_tele.git"
SERVICE_NAME="bot-tele"

echo "=== Cài Telegram Relay Bot ==="

dnf install -y python39 python39-pip git curl

if [ -d "$APP_DIR/.git" ]; then
  echo "Cập nhật code..."
  git -C "$APP_DIR" pull --ff-only
else
  echo "Clone repo..."
  mkdir -p "$(dirname "$APP_DIR")"
  git clone "$REPO_URL" "$APP_DIR"
fi

cd "$APP_DIR"

if [ ! -d ".venv" ]; then
  echo "Tạo virtualenv..."
  python3.9 -m venv .venv
fi

source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo ""
  echo "!!! Chưa có .env — hãy upload file .env từ máy Windows hoặc sửa:"
  echo "    nano $APP_DIR/.env"
  echo ""
fi

if [ ! -f "mappings.json" ]; then
  cp mappings.example.json mappings.json
  echo "Đã tạo mappings.json mẫu — upload file thật từ máy cũ nếu cần."
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

if grep -q "thay_token_botfather_vao_day" .env 2>/dev/null; then
  echo ""
  echo "!!! .env chưa có token thật — chưa start bot."
  echo "    Sửa .env rồi chạy: systemctl start ${SERVICE_NAME}"
  exit 0
fi

systemctl restart "$SERVICE_NAME"
sleep 2
systemctl status "$SERVICE_NAME" --no-pager

echo ""
echo "=== Xong ==="
echo "Xem log: journalctl -u ${SERVICE_NAME} -f"
