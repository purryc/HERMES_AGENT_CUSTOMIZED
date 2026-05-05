#!/usr/bin/env bash
set -euo pipefail

HERMES_HOME="/root/.hermes"
HERMES_BIN="/root/.local/bin/hermes"
PROJECT_ROOT="/root/.hermes/hermes-agent"
SESSION_NAME="hermes"

rm -f "$HERMES_HOME/gateway.pid" "$HERMES_HOME/gateway_state.json"
tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true
pkill -f 'hermes gateway run --accept-hooks' || true
sleep 2

tmux new-session -d -s "$SESSION_NAME" "cd $PROJECT_ROOT && PYTHONPATH=$PROJECT_ROOT $HERMES_BIN gateway run --accept-hooks"
sleep 6

PYTHONPATH="$PROJECT_ROOT" "$HERMES_BIN" gateway status || true
tmux list-sessions 2>/dev/null || true
