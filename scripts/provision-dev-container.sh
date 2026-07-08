#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Prefer system docker socket if Docker Desktop context is unavailable
if ! docker info >/dev/null 2>&1 && [[ -S /var/run/docker.sock ]]; then
  export DOCKER_HOST="unix:///var/run/docker.sock"
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker not installed. Install Docker Desktop (Mac) or docker.io (Linux)."
  exit 1
fi

mkdir -p demo-vm/keys demo-vm/staging
if [[ ! -f demo-vm/keys/pilot_push_key ]]; then
  ssh-keygen -t ed25519 -N "" -f demo-vm/keys/pilot_push_key -C pilot-rail-push
  cp demo-vm/keys/pilot_push_key.pub demo-container/ssh/authorized_keys
  echo "Generated push SSH key pair in demo-vm/keys/"
fi

docker compose build pilot-dev
docker compose up -d pilot-dev
echo ""
echo "Container pilot-dev is ready (SSH endpoint: 127.0.0.1:2222)"
echo "  Dashboard: Workstations tab → Deploy Gate"
echo "  Shell:     bash scripts/container-ops.sh shell"
