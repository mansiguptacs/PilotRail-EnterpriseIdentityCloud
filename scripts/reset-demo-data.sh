#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

API_BASE="${PILOT_API_BASE:-http://localhost:8000/api}"
CLEAR_WORKSTATIONS="${CLEAR_WORKSTATIONS:-false}"
REVIEWER="${REVIEWER_INITIALS:-SEC}"

payload=$(cat <<EOF
{
  "reviewer_initials": "$REVIEWER",
  "clear_workstations": $CLEAR_WORKSTATIONS
}
EOF
)

echo "Resetting demo data via $API_BASE/admin/reset-demo ..."
response=$(curl -sS -X POST "$API_BASE/admin/reset-demo" \
  -H "Content-Type: application/json" \
  -d "$payload")

echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
