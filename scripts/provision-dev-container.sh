#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if ! docker info >/dev/null 2>&1 && [[ -S /var/run/docker.sock ]]; then
  export DOCKER_HOST="unix:///var/run/docker.sock"
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker not installed. Install Docker Desktop (Mac) or docker.io (Linux)."
  exit 1
fi

mkdir -p demo-vm/keys demo-vm/staging backend/data
if [[ ! -f demo-vm/keys/pilot_push_key ]]; then
  ssh-keygen -t ed25519 -N "" -f demo-vm/keys/pilot_push_key -C pilot-rail-push
  cp demo-vm/keys/pilot_push_key.pub demo-container/ssh/authorized_keys
  echo "Generated push SSH key pair in demo-vm/keys/"
fi

docker compose build
docker compose up -d
echo ""
echo "Demo stack is up (backend :8000, frontend :5173, pilot-dev :2222)"
echo "  Quick start: bash scripts/demo-start.sh"
echo "  Dashboard:   http://127.0.0.1:5173"
echo "  Shell:       bash scripts/container-ops.sh shell"
