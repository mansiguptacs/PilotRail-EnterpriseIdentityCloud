#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
source "$REPO/scripts/enable-gate.sh"
cd "$REPO/demo-workspace"
cp scenarios/risky_contractor_admin.tf main.tf
echo ""
echo "Step 1: terraform apply (should FAIL FAST — no waiting)"
terraform apply -input=false || true
echo ""
echo "Step 2: Open http://127.0.0.1:5173 → Notifications tab"
echo "        Approve as SEC in dashboard"
echo ""
echo "Step 3: Re-run: terraform apply (should proceed with prior approval)"
echo "        (run manually after approving)"
