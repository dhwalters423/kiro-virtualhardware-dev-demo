#!/bin/bash
# deploy.sh — Deploy pi-security-cam to a Raspberry Pi over SSH
# Uses SSH multiplexing so you only enter your password once.
set -euo pipefail

SCRIPT_DIR="$(dirname "$(realpath "$0")")"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_DIR/.env"

# --- Load .env ---
if [ ! -f "$ENV_FILE" ]; then
    echo "Error: .env file not found at $ENV_FILE"
    echo "Copy .env.example to .env and fill in your Pi credentials:"
    echo "  cp .env.example .env"
    exit 1
fi

set -a
source "$ENV_FILE"
set +a

# --- Validate required variables ---
if [ -z "${PI_HOST:-}" ]; then
    echo "Error: PI_HOST is not set in .env"
    exit 1
fi

PI_USER="${PI_USER:-pi}"
REMOTE_DIR="~/pi-security-cam"

# --- SSH multiplexing (one password prompt for the whole script) ---
CTRL_SOCKET="/tmp/pi-deploy-$$"
SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=10"
SSH_OPTS="$SSH_OPTS -o ControlMaster=auto -o ControlPath=$CTRL_SOCKET -o ControlPersist=60"
if [ -n "${PI_SSH_KEY:-}" ]; then
    SSH_OPTS="$SSH_OPTS -i $PI_SSH_KEY"
fi
if [ -n "${PI_JUMP_HOST:-}" ]; then
    SSH_OPTS="$SSH_OPTS -J $PI_JUMP_HOST"
fi

cleanup() {
    ssh -o ControlPath=$CTRL_SOCKET -O exit "$PI_USER@$PI_HOST" 2>/dev/null || true
}
trap cleanup EXIT

run_ssh() {
    ssh $SSH_OPTS "$PI_USER@$PI_HOST" "$@"
}

run_scp() {
    scp $SSH_OPTS "$@"
}

echo "==> Deploying to $PI_USER@$PI_HOST (via ${PI_JUMP_HOST:-direct})..."
echo "==> Opening SSH connection (you may be prompted for a password once)..."

# --- Open master connection ---
run_ssh "echo 'Connected to Pi'"

# --- Stop any existing instance ---
echo "==> Stopping existing instance"
run_ssh 'bash -s' << 'KILL_SCRIPT'
for pid in $(ps aux | grep "[p]ython.*src.main" | awk "{print \$2}"); do
    kill "$pid" 2>/dev/null
done
sleep 2
KILL_SCRIPT

# --- Clean old files ---
echo "==> Cleaning old files on Pi"
run_ssh "rm -rf ~/pi-security-cam && mkdir -p ~/pi-security-cam"

# --- Copy application files ---
echo "==> Copying application files via SCP"
run_scp -r \
    "$PROJECT_DIR/src" \
    "$PROJECT_DIR/config.json" \
    "$PROJECT_DIR/requirements.txt" \
    "$PROJECT_DIR/tests" \
    "$PROJECT_DIR/pytest.ini" \
    "$PI_USER@$PI_HOST:$REMOTE_DIR/"

# --- Ensure OpenCV with GUI/GTK support ---
echo "==> Ensuring system OpenCV with GTK support..."
run_ssh "sudo apt-get update && sudo apt-get install -y python3-opencv"
# Remove pip opencv-python so the system package (with GTK) takes priority
run_ssh "pip uninstall -y opencv-python opencv-python-headless 2>/dev/null || true"

# --- Install remaining Python dependencies (skip opencv-python) ---
echo "==> Installing Python dependencies on Pi"
run_ssh "cd $REMOTE_DIR && pip install ultralytics pytest hypothesis pytest-json-report"

# --- Start application as background process ---
echo "==> Starting application on Pi (backgrounding)..."
run_ssh "nohup bash -c 'cd ~/pi-security-cam && DISPLAY=:0 python -m src.main --config config.json > app.log 2>&1 & echo \$! > app.pid' &" &
sleep 5

# --- Show startup log ---
echo "==> Application log (first 20 lines):"
run_ssh "head -20 ~/pi-security-cam/app.log 2>/dev/null || echo 'No log yet'"

# --- Verify it's running ---
echo "==> Verifying application is running..."
run_ssh "pgrep -f 'src.main' > /dev/null && echo 'App is running' || echo 'WARNING: App is not running'"

echo "==> Deployment complete."
