#!/usr/bin/env bash
# One-command Pilot Rail enterprise demo bootstrap (all services in Docker).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

AUTO_PUSH=1
REVIEWER="SEC"

usage() {
  cat <<EOF
Usage: $0 [options]

  Starts backend, frontend, and pilot-dev via docker compose.
  Optionally auto-deploys the apply gate.

Options:
  --no-push           Skip auto deploy-gate (use dashboard for IT push demo)
  --reviewer INITIALS Reviewer for auto-push (default: SEC)
  -h, --help          Show this help

Examples:
  bash scripts/demo-start.sh              # full quick-start (auto-push)
  bash scripts/demo-start.sh --no-push    # infra only — click Deploy Gate yourself
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-push) AUTO_PUSH=0; shift ;;
    --reviewer) REVIEWER="${2:?--reviewer requires initials}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1"; usage; exit 1 ;;
  esac
done

# Docker socket fallback (Docker Desktop vs system docker)
if ! docker info >/dev/null 2>&1 && [[ -S /var/run/docker.sock ]]; then
  export DOCKER_HOST="unix:///var/run/docker.sock"
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker not installed. Install Docker Desktop (Mac) or docker.io (Linux)."
  exit 1
fi

log() { echo "==> $*"; }

wait_for_url() {
  local url="$1"
  local label="$2"
  local tries="${3:-60}"
  for ((i = 1; i <= tries; i++)); do
    if curl -sf "$url" >/dev/null 2>&1; then
      echo "  OK   $label"
      return 0
    fi
    sleep 1
  done
  echo "  FAIL $label (timed out waiting for $url)"
  return 1
}

log "Pilot Rail demo bootstrap (Docker Compose)"
log "Repository: $REPO_ROOT"
echo ""

# SSH keys for IT push (host-side; mounted into backend container)
mkdir -p demo-vm/keys demo-vm/staging backend/data
if [[ ! -f demo-vm/keys/pilot_push_key ]]; then
  ssh-keygen -t ed25519 -N "" -f demo-vm/keys/pilot_push_key -C pilot-rail-push
  cp demo-vm/keys/pilot_push_key.pub demo-container/ssh/authorized_keys
  echo "  Generated push SSH key pair in demo-vm/keys/"
fi

log "Building and starting services (backend, frontend, pilot-dev)..."
docker compose build
docker compose up -d

log "Waiting for backend..."
wait_for_url "http://127.0.0.1:8000/health" "backend health"

log "Waiting for frontend..."
wait_for_url "http://127.0.0.1:5173" "frontend dev server" 60

log "Checking pilot-dev can reach API..."
docker exec pilot-dev curl -sf http://backend:8000/health >/dev/null
echo "  OK   pilot-dev → backend API"

if [[ "$AUTO_PUSH" -eq 1 ]]; then
  log "Auto-deploying apply gate to pilot-dev as $REVIEWER..."
  if response=$(curl -sf -X POST http://127.0.0.1:8000/api/workstations/push \
    -H "Content-Type: application/json" \
    -d "{\"vm_name\":\"pilot-dev\",\"ip\":\"pilot-dev\",\"ssh_port\":22,\"ssh_user\":\"developer\",\"reviewer_initials\":\"$REVIEWER\"}"); then
    if echo "$response" | grep -qE '"state"\s*:\s*"(DEPLOYED|DEPLOYING)"'; then
      echo "  OK   gate deployed"
    else
      echo "  WARN gate push returned unexpected state — check dashboard"
    fi
  else
    echo "  WARN gate push failed — deploy manually from dashboard"
  fi
else
  log "Skipping auto-push (--no-push). Deploy gate from dashboard → Workstations."
fi

log "Running preflight checks..."
bash scripts/demo-preflight.sh

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  Pilot Rail demo is ready"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "  Dashboard:  http://127.0.0.1:5173  (Workstations tab)"
echo "  API:        http://127.0.0.1:8000"
echo ""
echo "  Developer shell:"
echo "    bash scripts/container-ops.sh shell"
echo ""
echo "  Try risky scenario:"
echo "    cp scenarios/risky_contractor_admin.tf main.tf"
echo "    terraform apply"
echo ""
if [[ "$AUTO_PUSH" -eq 0 ]]; then
  echo "  Next: Dashboard → Workstations → Deploy Gate (as $REVIEWER)"
  echo ""
fi
echo "  Logs:  docker compose logs -f backend|frontend|pilot-dev"
echo "  Stop:  bash scripts/demo-stop.sh"
echo ""
