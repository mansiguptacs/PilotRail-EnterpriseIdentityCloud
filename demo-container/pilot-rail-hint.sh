# Shown when opening a root shell — gate is installed for the developer user.
if [ "$(id -u)" -eq 0 ] && [ -t 1 ]; then
  echo ""
  echo "[pilot-rail] This is a root shell. The enterprise apply gate is installed for user 'developer'."
  echo "[pilot-rail] From the host:  bash scripts/container-ops.sh shell"
  echo "[pilot-rail] From here:       su - developer"
  echo ""
fi
