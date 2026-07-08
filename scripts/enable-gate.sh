#!/usr/bin/env bash
# Source this before running terraform in demo-workspace:
#   source scripts/enable-gate.sh

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PATH="$REPO_ROOT/cli/shim:$PATH"
export PILOT_REAL_TERRAFORM="$REPO_ROOT/backend/bin/terraform"
export PILOT_API_BASE="${PILOT_API_BASE:-http://127.0.0.1:8000/api}"

SHIM="$(command -v terraform)"
if [[ "$SHIM" != "$REPO_ROOT/cli/shim/terraform" ]]; then
  echo "ERROR: Pilot Rail shim is NOT active on PATH."
  echo "  Expected: $REPO_ROOT/cli/shim/terraform"
  echo "  Got:      ${SHIM:-<not found>}"
  echo ""
  echo "Do NOT run $PILOT_REAL_TERRAFORM apply directly — that bypasses the gate."
  return 1 2>/dev/null || exit 1
fi

if [[ ! -x "$PILOT_REAL_TERRAFORM" ]]; then
  echo "ERROR: Real terraform not found. Run: bash scripts/install-terraform.sh"
  return 1 2>/dev/null || exit 1
fi

if ! curl -sf "$PILOT_API_BASE/../health" >/dev/null 2>&1; then
  echo "WARNING: Pilot Rail backend not reachable at ${PILOT_API_BASE%/api}"
  echo "Start it with: cd backend && .venv/bin/uvicorn app.main:app --reload"
fi

echo "Pilot Rail apply gate ENABLED"
echo "  shim:     $SHIM"
echo "  real tf:  $PILOT_REAL_TERRAFORM"
echo "  api:      $PILOT_API_BASE"
