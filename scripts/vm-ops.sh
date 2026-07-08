#!/usr/bin/env bash
# Multipass VM operations for Pilot Rail demo.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=multipass-common.sh
source "$REPO_ROOT/scripts/multipass-common.sh"

VM_NAME="${VM_NAME:-pilot-dev}"

cmd="${1:-}"

case "$cmd" in
  start)
    multipass start "$VM_NAME"
    echo "VM $VM_NAME started"
    ;;
  stop)
    multipass stop "$VM_NAME"
    echo "VM $VM_NAME stopped"
    ;;
  shell)
    multipass shell "$VM_NAME"
    ;;
  ip)
    multipass_vm_ip "$VM_NAME"
    ;;
  list)
    multipass list
    ;;
  agent-log)
    multipass exec "$VM_NAME" -- tail -f "$HOME/.pilot-rail/agent.log"
    ;;
  status)
    multipass info "$VM_NAME"
    echo "Host API: $(multipass_host_api_url "$VM_NAME")"
    ;;
  *)
    echo "Usage: $0 {start|stop|shell|ip|list|agent-log|status}"
    exit 1
    ;;
esac
