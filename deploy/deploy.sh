#!/usr/bin/env bash
# Deploys/updates the Bonus Hedge Finder web GUI on this machine.
# Run this ON THE VPS (not from your laptop):
#   curl -fsSL https://raw.githubusercontent.com/louaih/bonus-hedge/claude/web-gui-vps-deploy-snxay6/deploy/deploy.sh | bash
# or, if you already cloned the repo:
#   bash deploy/deploy.sh
set -euo pipefail

REPO_URL="https://github.com/louaih/bonus-hedge.git"
BRANCH="${BRANCH:-claude/web-gui-vps-deploy-snxay6}"
APP_DIR="${APP_DIR:-/opt/bonus-hedge}"

if [ -d "$APP_DIR/.git" ]; then
  echo "==> Updating existing checkout at $APP_DIR"
  git -C "$APP_DIR" fetch origin "$BRANCH"
  git -C "$APP_DIR" checkout "$BRANCH"
  git -C "$APP_DIR" pull origin "$BRANCH"
else
  echo "==> Cloning $REPO_URL into $APP_DIR"
  git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
fi

cd "$APP_DIR"

echo "==> Setting up virtualenv"
python3 -m venv .venv
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r requirements.txt

if [ ! -f web_gui_auth.json ] && [ -z "${WEBGUI_USER:-}" ]; then
  echo "==> Generating web GUI login credentials"
  .venv/bin/python3 -c "import web_gui"
fi

echo "==> Installing systemd service"
cp deploy/bonus-hedge-web.service /etc/systemd/system/bonus-hedge-web.service
systemctl daemon-reload
systemctl enable --now bonus-hedge-web
systemctl restart bonus-hedge-web

echo "==> Done. Service status:"
systemctl --no-pager status bonus-hedge-web || true

echo
echo "==> Login credentials (also saved in $APP_DIR/web_gui_auth.json):"
cat "$APP_DIR/web_gui_auth.json" 2>/dev/null || echo "  (using WEBGUI_USER/WEBGUI_PASSWORD env vars instead)"
echo
echo "==> Open: http://$(curl -s -4 ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}'):8080"
