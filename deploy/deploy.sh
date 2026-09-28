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

echo "==> Picking a Python interpreter (need 3.9+)"
PYTHON_BIN=""
for candidate in python3.13 python3.12 python3.11 python3.10 python3.9 python3; do
  if command -v "$candidate" >/dev/null 2>&1; then
    ver="$("$candidate" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')"
    major="${ver%%.*}"
    minor="${ver#*.}"
    if [ "$major" -eq 3 ] && [ "$minor" -ge 9 ]; then
      PYTHON_BIN="$candidate"
      break
    fi
  fi
done
if [ -z "$PYTHON_BIN" ]; then
  echo "ERROR: no Python 3.9+ interpreter found (checked python3.9-3.13 and python3)." >&2
  echo "Install one, e.g. on AlmaLinux/RHEL: dnf install -y python3.11" >&2
  exit 1
fi
echo "    using $PYTHON_BIN ($("$PYTHON_BIN" --version))"

echo "==> Setting up virtualenv"
rm -rf .venv
"$PYTHON_BIN" -m venv .venv
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
