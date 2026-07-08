#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if ! docker info >/dev/null 2>&1 && [[ -S /var/run/docker.sock ]]; then
  export DOCKER_HOST="unix:///var/run/docker.sock"
fi

docker compose down
echo "All demo services stopped."
