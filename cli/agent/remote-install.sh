#!/usr/bin/env bash
# Runs on the remote workstation during IT push deploy.
set -euo pipefail

PILOT_HOME="${PILOT_HOME:-$HOME/.pilot-rail}"
PILOT_API_BASE="${PILOT_API_BASE:?PILOT_API_BASE required}"
WORKSTATION_ID="${WORKSTATION_ID:?WORKSTATION_ID required}"
DEPLOYED_BY="${DEPLOYED_BY:-IT-ADMIN}"
SHIM_VERSION="${SHIM_VERSION:-0.1.0}"

mkdir -p "$PILOT_HOME"/{shim,bin,agent,workspace}

# Config
cat > "$PILOT_HOME/config.env" <<EOF
export PILOT_API_BASE="$PILOT_API_BASE"
export PILOT_WORKSTATION_ID="$WORKSTATION_ID"
export PILOT_HOME="$PILOT_HOME"
export PILOT_REAL_TERRAFORM="$PILOT_HOME/bin/terraform"
EOF

# Install terraform if missing
if [[ ! -x "$PILOT_HOME/bin/terraform" ]]; then
  ARCH=$(uname -m)
  case "$ARCH" in
    x86_64) TF_ARCH="amd64" ;;
    aarch64|arm64) TF_ARCH="arm64" ;;
    *) echo "Unsupported arch: $ARCH"; exit 1 ;;
  esac
  TF_VERSION="1.9.8"
  TMP=$(mktemp -d)
  curl -fsSL "https://releases.hashicorp.com/terraform/${TF_VERSION}/terraform_${TF_VERSION}_linux_${TF_ARCH}.zip" -o "$TMP/terraform.zip"
  python3 -c "
import zipfile, sys
with zipfile.ZipFile(sys.argv[1]) as z:
    z.extract('terraform', sys.argv[2])
" "$TMP/terraform.zip" "$PILOT_HOME/bin"
  chmod +x "$PILOT_HOME/bin/terraform"
  rm -rf "$TMP"
fi

chmod +x "$PILOT_HOME/shim/terraform" "$PILOT_HOME/agent/pilot-rail-agent" "$PILOT_HOME/agent/pilot-rail-show-notice" 2>/dev/null || true

# Standard workspace path developers expect (demo-workspace -> IT-pushed workspace)
if [[ -L "$HOME/demo-workspace" ]] || [[ -d "$HOME/demo-workspace" && -z "$(ls -A "$HOME/demo-workspace" 2>/dev/null)" ]]; then
  rm -rf "$HOME/demo-workspace" 2>/dev/null || true
fi
if [[ ! -e "$HOME/demo-workspace" ]]; then
  ln -sfn "$PILOT_HOME/workspace" "$HOME/demo-workspace"
fi

# Enable gate on shell start (interactive bash)
GATE_HOOK='[[ $- == *i* ]] && source "$HOME/.pilot-rail/enable-gate.sh" 2>/dev/null || true'
if ! grep -q "pilot-rail/enable-gate" "$HOME/.bashrc" 2>/dev/null; then
  echo "$GATE_HOOK" >> "$HOME/.bashrc"
fi

# enable-gate.sh on remote — sourced automatically from .bashrc on every shell
cat > "$PILOT_HOME/enable-gate.sh" <<'GATEEOF'
#!/usr/bin/env bash
# Pilot Rail enterprise apply gate (IT-deployed shim on PATH)
if [[ -n "${PILOT_RAIL_GATE_LOADED:-}" ]]; then
  return 0 2>/dev/null || exit 0
fi
export PILOT_RAIL_GATE_LOADED=1

if [[ -f "$HOME/.pilot-rail/config.env" ]]; then
  # shellcheck source=/dev/null
  source "$HOME/.pilot-rail/config.env"
fi
export PATH="$HOME/.pilot-rail/shim:$PATH"
export PILOT_REAL_TERRAFORM="${PILOT_REAL_TERRAFORM:-$HOME/.pilot-rail/bin/terraform}"

if [[ $- == *i* ]]; then
  deployed_by="$(python3 -c "import json,pathlib; d=json.loads(pathlib.Path.home().joinpath('.pilot-rail/installed.json').read_text()); print(d.get('deployed_by','IT'))" 2>/dev/null || echo IT)"
  echo ""
  echo "[pilot-rail] Enterprise-managed Terraform is active on this workstation."
  echo "[pilot-rail] Deployed by: ${deployed_by}  |  terraform: $(command -v terraform)"
  echo "[pilot-rail] terraform apply is governed — changes require Pilot Rail approval."
  echo ""
  cd "$HOME/.pilot-rail/workspace" 2>/dev/null || cd "$HOME/demo-workspace" 2>/dev/null || true
fi
GATEEOF
chmod +x "$PILOT_HOME/enable-gate.sh"

# Prompt hook for in-session notices
PROMPT_HOOK='[ -f "$HOME/.pilot-rail/pending-notice.txt" ] && cat "$HOME/.pilot-rail/pending-notice.txt" && rm -f "$HOME/.pilot-rail/pending-notice.txt"'
if ! grep -q "pilot-rail/pending-notice" "$HOME/.bashrc" 2>/dev/null; then
  cat >> "$HOME/.bashrc" <<EOF

# Pilot Rail in-session notices
if [[ -z "\${PILOT_RAIL_PROMPT_HOOK:-}" ]]; then
  export PILOT_RAIL_PROMPT_HOOK=1
  if [[ -n "\$PROMPT_COMMAND" ]]; then
    PROMPT_COMMAND='$PROMPT_HOOK; '"\$PROMPT_COMMAND"
  else
    PROMPT_COMMAND='$PROMPT_HOOK'
  fi
fi
EOF
fi

# Login banner helper
if ! grep -q "pilot-rail-show-notice" "$HOME/.bashrc" 2>/dev/null; then
  echo '[ -f "$HOME/.pilot-rail/installed.json" ] && "$HOME/.pilot-rail/agent/pilot-rail-show-notice" 2>/dev/null || true' >> "$HOME/.bashrc"
fi

# Installed manifest
rm -f "$PILOT_HOME/.notice_shown" 2>/dev/null || true
cat > "$PILOT_HOME/installed.json" <<EOF
{
  "deployed_by": "$DEPLOYED_BY",
  "deployed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "shim_version": "$SHIM_VERSION",
  "control_plane": "$PILOT_API_BASE"
}
EOF

# Pending notice for open terminals
cat > "$PILOT_HOME/pending-notice.txt" <<EOF
[pilot-rail] NOTICE: IT admin ($DEPLOYED_BY) deployed the Pilot Rail apply gate.
[pilot-rail] terraform apply on this workstation is now governed.
[pilot-rail] Control plane: $PILOT_API_BASE
EOF

# Start agent
if [[ -f "$PILOT_HOME/agent.pid" ]]; then
  old_pid=$(cat "$PILOT_HOME/agent.pid" 2>/dev/null || true)
  if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
    kill "$old_pid" 2>/dev/null || true
  fi
fi
nohup "$PILOT_HOME/agent/pilot-rail-agent" >> "$PILOT_HOME/agent.log" 2>&1 &
echo $! > "$PILOT_HOME/agent.pid"

echo "Pilot Rail apply gate installed successfully"
