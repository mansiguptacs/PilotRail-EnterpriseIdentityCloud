#!/usr/bin/env bash
# One-command Pilot Rail enterprise demo bootstrap.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

AUTO_PUSH=1
REVIEWER="SEC"
DEMO_DIR="$REPO_ROOT/.demo"
BACKEND_PID="$DEMO_DIR/backend.pid"
FRONTEND_PID="$DEMO_DIR/frontend.pid"
BACKEND_LOG="$DEMO_DIR/backend.log"
FRONTEND_LOG="$DEMO_DIR/frontend.log"

usage() {
  cat <<EOF
Usage: $0 [options]

  Starts container, backend, and frontend. Optionally auto-deploys the apply gate.

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

mkdir -p "$DEMO_DIR" demo-vm/keys demo-vm/staging

# Docker socket fallback (Docker Desktop vs system docker)
if ! docker info >/dev/null 2>&1 && [[ -S /var/run/docker.sock ]]; then
  export DOCKER_HOST="unix:///var/run/docker.sock"
fi

log() { echo "==> $*"; }

wait_for_url() {
  local url="$1"
  local label="$2"
  local tries="${3:-30}"
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

start_if_dead() {
  local pid_file="$1"
  if [[ -f "$pid_file" ]]; then
    local pid
    pid="$(cat "$pid_file")"
    if kill -0 "$pid" 2>/dev/null; then
      return 0
    fi
  fi
  return 1
}

log "Pilot Rail demo bootstrap"
log "Repository: $REPO_ROOT"
echo ""

# 1. Container
log "Starting pilot-dev container..."
bash scripts/provision-dev-container.sh

# 2. Backend
log "Starting backend on :8000..."
if curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1; then
  echo "  OK   backend already running"
else
  if [[ ! -d backend/.venv ]]; then
    python3 -m venv backend/.venv
  fi
  backend/.venv/bin/pip install -q -r backend/requirements.txt
  if start_if_dead "$BACKEND_PID"; then
    echo "  OK   backend already running (pid $(cat "$BACKEND_PID"))"
  else
    nohup backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 \
      >"$BACKEND_LOG" 2>&1 &
    echo $! >"$BACKEND_PID"
    wait_for_url "http://127.0.0.1:8000/health" "backend health"
  fi
fi

# 3. Frontend
log "Starting frontend on :5173..."
if curl -sf http://127.0.0.1:5173 >/dev/null 2>&1; then
  echo "  OK   frontend already running"
else
  if [[ ! -d frontend/node_modules ]]; then
    (cd frontend && npm install --silent)
  fi
  if start_if_dead "$FRONTEND_PID"; then
    echo "  OK   frontend already running (pid $(cat "$FRONTEND_PID"))"
  else
    nohup bash -lc "cd frontend && npm run dev -- --host 127.0.0.1 --port 5173" \
      >"$FRONTEND_LOG" 2>&1 &
    echo $! >"$FRONTEND_PID"
    wait_for_url "http://127.0.0.1:5173" "frontend dev server" 45
  fi
fi

# 4. Container → API connectivity
log "Checking container can reach host API..."
wait_for_url "http://127.0.0.1:8000/health" "host API" 5
docker exec pilot-dev curl -sf http://host.docker.internal:8000/health >/dev/null
echo "  OK   container → host API"

# 5. Auto-push gate (optional)
if [[ "$AUTO_PUSH" -eq 1 ]]; then
  log "Auto-deploying apply gate to pilot-dev as $REVIEWER..."
  if response=$(curl -sf -X POST http://127.0.0.1:8000/api/workstations/push \
    -H "Content-Type: application/json" \
    -d "{\"ip\":\"127.0.0.1\",\"vm_name\":\"pilot-dev\",\"ssh_port\":2222,\"ssh_user\":\"developer\",\"reviewer_initials\":\"$REVIEWER\"}"); then
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

# 6. Final preflight
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
echo "  Logs:  .demo/backend.log  .demo/frontend.log"
echo "  Stop:  bash scripts/demo-stop.sh"
echo ""
