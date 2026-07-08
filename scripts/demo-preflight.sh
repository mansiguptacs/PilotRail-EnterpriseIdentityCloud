#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PASS=0
FAIL=0
check() {
  local name="$1"
  shift
  if "$@"; then
    echo "  OK   $name"
    PASS=$((PASS + 1))
  else
    echo "  FAIL $name"
    FAIL=$((FAIL + 1))
  fi
}

echo "Pilot Rail demo preflight"
echo "========================="

check "docker installed" command -v docker
check "docker daemon running" docker info
check "pilot-dev container running" docker ps --filter name=pilot-dev --filter status=running --format '{{.Names}}' | grep -q pilot-dev
check "SSH key present" test -f demo-vm/keys/pilot_push_key
check "bundle staging writable" test -w demo-vm/staging || mkdir -p demo-vm/staging
check "backend health" curl -sf http://127.0.0.1:8000/health
check "container API reachability" docker exec pilot-dev curl -sf http://host.docker.internal:8000/health
check "workstation discovery" curl -sf http://127.0.0.1:8000/api/workstations/discover | grep -q pilot-dev

echo ""
echo "Passed: $PASS  Failed: $FAIL"
if [[ $FAIL -gt 0 ]]; then
  exit 1
fi
echo "Ready for demo."
