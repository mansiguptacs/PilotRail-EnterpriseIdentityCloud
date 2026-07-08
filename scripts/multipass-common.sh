#!/usr/bin/env bash
# Shared Multipass helpers (1.16+ uses --format json, not template strings).
set -euo pipefail

# Usage: multipass_vm_ip <vm-name>
multipass_vm_ip() {
  local name="${1:?vm name required}"
  if ! command -v multipass >/dev/null 2>&1; then
    return 1
  fi
  multipass info "$name" --format json 2>/dev/null | python3 -c "
import json, sys
name = sys.argv[1]
try:
    data = json.load(sys.stdin)
except json.JSONDecodeError:
    sys.exit(1)
ips = data.get('info', {}).get(name, {}).get('ipv4', [])
print(ips[0] if ips else '')
" "$name"
}

# Usage: multipass_host_api_url <vm-name>
multipass_host_api_url() {
  local _vm_name="${1:-pilot-dev}"
  # Host side of the Multipass bridge (e.g. 10.132.47.1 on mpqemubr0)
  local bridge_ip
  bridge_ip=$(ip -4 route show dev mpqemubr0 2>/dev/null | awk '/proto kernel/ {print $NF; exit}')
  if [[ -n "$bridge_ip" ]]; then
    echo "http://${bridge_ip}:8000"
    return 0
  fi
  local vm_ip
  vm_ip=$(multipass_vm_ip "$_vm_name" 2>/dev/null || true)
  if [[ -n "$vm_ip" ]]; then
    echo "http://${vm_ip%.*}.1:8000"
    return 0
  fi
  echo "http://127.0.0.1:8000"
}

# Usage: multipass_install_ssh_key <vm-name> <pubkey-file>
multipass_install_ssh_key() {
  local name="${1:?}"
  local pub_file="${2:?}"
  multipass transfer "$pub_file" "${name}:/tmp/pilot_push_key.pub"
  multipass exec "$name" -- bash -lc '
    mkdir -p ~/.ssh && chmod 700 ~/.ssh
    touch ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys
    if ! grep -qF "pilot-rail-push" ~/.ssh/authorized_keys 2>/dev/null; then
      cat /tmp/pilot_push_key.pub >> ~/.ssh/authorized_keys
    fi
    rm -f /tmp/pilot_push_key.pub
  '
}
