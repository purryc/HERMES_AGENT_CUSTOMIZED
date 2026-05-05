#!/usr/bin/env bash
set -euo pipefail

SESSION_NAME="hermes-dashboard"
PORT="9119"
PROJECT_ROOT="/root/.hermes/hermes-agent"

if ss -ltn | grep -q "127.0.0.1:$PORT"; then
  pkill -f "hermes dashboard" || true
  sleep 2
fi

tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true
tmux new-session -d -s "$SESSION_NAME" "cd $PROJECT_ROOT && PYTHONPATH=$PROJECT_ROOT /root/.local/bin/hermes dashboard --no-open --tui"

for _ in $(seq 1 20); do
  if ss -ltn | grep -q "127.0.0.1:$PORT"; then
    exit 0
  fi
  sleep 1
done

tmux capture-pane -pt "$SESSION_NAME" -S -120 2>/dev/null || true
exit 1
