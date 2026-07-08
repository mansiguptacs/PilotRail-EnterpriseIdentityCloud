#!/usr/bin/env bash
set -euo pipefail

VERSION="1.9.8"
ARCH="linux_amd64"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$REPO_ROOT/backend/bin"
ZIP="terraform_${VERSION}_${ARCH}.zip"
URL="https://releases.hashicorp.com/terraform/${VERSION}/${ZIP}"

mkdir -p "$DEST"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

echo "Downloading Terraform ${VERSION}..."
curl -fsSL "$URL" -o "$TMP/$ZIP"
unzip -q "$TMP/$ZIP" -d "$TMP"
mv "$TMP/terraform" "$DEST/terraform"
chmod +x "$DEST/terraform"
chmod +x "$REPO_ROOT/cli/shim/terraform"

echo "Installed: $("$DEST/terraform" version | head -1)"
echo "Shim: $REPO_ROOT/cli/shim/terraform"
echo ""
echo "To enable the apply gate:"
echo "  export PATH=\"$REPO_ROOT/cli/shim:\$PATH\""
echo "  export PILOT_REAL_TERRAFORM=\"$DEST/terraform\""
