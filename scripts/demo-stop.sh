#!/usr/bin/env bash
# Stop background demo services started by demo-start.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEMO_DIR="$REPO_ROOT/.demo"

stop_pid_file() {
  local name="$1"
  local pid_file="$2"
  if [[ -f "$pid_file" ]]; then
    local pid
    pid="$(cat "$pid_file")"
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
      echo "Stopped $name (pid $pid)"
    fi
    rm -f "$pid_file"
  fi
}

stop_pid_file "backend" "$DEMO_DIR/backend.pid"
stop_pid_file "frontend" "$DEMO_DIR/frontend.pid"

echo "Container still running. To stop: bash scripts/container-ops.sh stop"
