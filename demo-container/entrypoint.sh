#!/usr/bin/env bash
set -euo pipefail

mkdir -p /var/run/sshd
/usr/sbin/sshd

HOST_API="${PILOT_HOST_API_URL:-http://host.docker.internal:8000}"
CONTAINER_NAME="${PILOT_CONTAINER_NAME:-pilot-dev}"
CONTAINER_ID="$(hostname)"
HOST_SSH_PORT="${PILOT_HOST_SSH_PORT:-2222}"

curl -sf -X POST "${HOST_API}/api/workstations/register" \
  -H "Content-Type: application/json" \
  -d "{\"hostname\":\"${CONTAINER_NAME}\",\"container_id\":\"${CONTAINER_ID}\",\"host_ssh_port\":${HOST_SSH_PORT},\"ip\":\"127.0.0.1\"}" \
  2>/dev/null || true

exec sleep infinity
