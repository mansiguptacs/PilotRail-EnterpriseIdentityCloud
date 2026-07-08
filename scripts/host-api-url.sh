#!/usr/bin/env bash
# Print the host API URL reachable from Multipass VMs.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=multipass-common.sh
source "$REPO_ROOT/scripts/multipass-common.sh"

VM_NAME="${1:-pilot-dev}"
multipass_host_api_url "$VM_NAME"
