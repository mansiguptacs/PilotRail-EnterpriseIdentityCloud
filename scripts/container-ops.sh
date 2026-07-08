#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

CMD="${1:-status}"
case "$CMD" in
  start)
    docker compose up -d
    ;;
  stop)
    docker compose stop
    ;;
  shell)
    echo "Opening developer shell (run from host, not inside container)."
    docker exec -it -u developer pilot-dev bash -lc 'exec bash -l'
    ;;
  agent-log)
    docker exec -u developer pilot-dev tail -f /home/developer/.pilot-rail/agent.log
    ;;
  status)
    docker compose ps
    ;;
  logs)
    docker compose logs -f "${2:-}"
    ;;
  rebuild)
    docker compose build pilot-dev
    docker compose up -d pilot-dev
    ;;
  *)
    echo "Usage: $0 {start|stop|shell|agent-log|status|logs|rebuild}"
    exit 1
    ;;
esac
