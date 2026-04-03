#!/bin/bash
# test.sh — Run pytest on the Pi and fetch results to local test-reporter/
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
CTRL_SOCKET="/tmp/pi-test-$$"
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

echo "==> Running tests on $PI_USER@$PI_HOST (via ${PI_JUMP_HOST:-direct})..."
echo "==> Opening SSH connection (you may be prompted for a password once)..."

# --- Open master connection ---
run_ssh "echo 'Connected to Pi'"

# --- Run pytest with JSON report on the Pi ---
run_ssh "cd $REMOTE_DIR && python -m pytest --on-device --json-report --json-report-file=results.json tests/ || true"

# --- Fetch results.json back to local machine ---
echo "==> Fetching test results..."
run_scp "$PI_USER@$PI_HOST:$REMOTE_DIR/results.json" "$PROJECT_DIR/test-reporter/results.json"

echo "==> Test results saved to test-reporter/results.json"
echo "    Open test-reporter/index.html in a browser to view results."
