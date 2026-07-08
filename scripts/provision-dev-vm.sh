#!/usr/bin/env bash
# Launch blank Multipass VM for enterprise workstation demo.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=multipass-common.sh
source "$REPO_ROOT/scripts/multipass-common.sh"

VM_NAME="${VM_NAME:-pilot-dev}"
# Minimal footprint — enough for terraform (local/null providers) + python shim + agent
VM_CPUS="${VM_CPUS:-1}"
VM_MEMORY="${VM_MEMORY:-1G}"
VM_DISK="${VM_DISK:-5G}"
KEY_DIR="$REPO_ROOT/demo-vm/keys"
KEY_FILE="$KEY_DIR/pilot_push_key"
PUB_FILE="$KEY_FILE.pub"

if ! command -v multipass >/dev/null 2>&1; then
  echo "ERROR: multipass not installed. Run: sudo snap install multipass"
  exit 1
fi

mkdir -p "$KEY_DIR"
if [[ ! -f "$KEY_FILE" ]]; then
  echo "Generating SSH demo keypair..."
  ssh-keygen -t ed25519 -f "$KEY_FILE" -N "" -C "pilot-rail-push"
fi

if multipass info "$VM_NAME" &>/dev/null; then
  echo "VM '$VM_NAME' already exists."
  echo "  (To recreate with new sizing: multipass delete $VM_NAME --purge && rerun this script)"
else
  echo "Launching $VM_NAME (${VM_CPUS} CPU, ${VM_MEMORY} RAM, ${VM_DISK} disk)..."
  multipass launch 24.04 \
    --name "$VM_NAME" \
    --cpus "$VM_CPUS" \
    --memory "$VM_MEMORY" \
    --disk "$VM_DISK"
fi

multipass start "$VM_NAME" 2>/dev/null || true

echo "Installing SSH public key for push deploy..."
multipass_install_ssh_key "$VM_NAME" "$PUB_FILE"

VM_IP=$(multipass_vm_ip "$VM_NAME")
HOST_API=$(multipass_host_api_url "$VM_NAME")

echo ""
echo "═══════════════════════════════════════════════════"
echo "  Pilot Dev VM ready: $VM_NAME"
echo "  Resources:  ${VM_CPUS} CPU, ${VM_MEMORY} RAM, ${VM_DISK} disk"
echo "  VM IP:      ${VM_IP:-unknown}"
echo "  Host API:   $HOST_API  (set PILOT_HOST_API_URL for push)"
echo "  SSH key:    $KEY_FILE"
echo ""
echo "  Next steps:"
echo "    1. Start backend:  cd backend && .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000"
echo "    2. Start frontend: cd frontend && npm run dev"
echo "    3. Open dashboard → Workstations tab → Deploy Gate"
echo "    4. Dev terminal:   bash scripts/vm-ops.sh shell"
echo "═══════════════════════════════════════════════════"
