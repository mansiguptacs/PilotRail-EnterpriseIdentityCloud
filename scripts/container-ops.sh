#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

CMD="${1:-status}"
case "$CMD" in
  start)
    docker compose up -d pilot-dev
    ;;
  stop)
    docker compose down
    ;;
  shell)
    echo "Opening developer shell (run this from the host, not inside the container)."
    docker exec -it -u developer -w /home/developer pilot-dev bash -l
    ;;
  agent-log)
    docker exec -u developer pilot-dev tail -f /home/developer/.pilot-rail/agent.log
    ;;
  status)
    docker ps --filter name=pilot-dev --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
    ;;
  rebuild)
    docker compose build pilot-dev
    docker compose up -d pilot-dev
    ;;
  *)
    echo "Usage: $0 {start|stop|shell|agent-log|status|rebuild}"
    exit 1
    ;;
esac
