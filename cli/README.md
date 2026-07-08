# Pilot Rail Terraform Apply Gate

The `terraform` command on your PATH is a **wrapper shim** that gates `terraform apply`
through the Pilot Rail policy engine.

## Setup (one time)

```bash
# From repo root
bash scripts/install-terraform.sh

export PATH="$(pwd)/cli/shim:$PATH"
export PILOT_REAL_TERRAFORM="$(pwd)/backend/bin/terraform"
export PILOT_API_BASE="http://127.0.0.1:8000/api"
```

Ensure the Pilot Rail backend is running (`uvicorn app.main:app` in `backend/`).

## How it works

1. `terraform init`, `plan`, `validate`, etc. pass through to the real binary unchanged.
2. `terraform apply` is intercepted:
   - Runs a real `terraform plan -out=pilot.tfplan`
   - Submits HCL + plan JSON + fingerprint to Pilot Rail
   - **Auto-approved** (no critical/high findings) → proceeds with apply immediately
   - **Blocked** (critical/high) → **fails fast** (exit 1), approver notified async
3. After admin approves in dashboard, dev **re-runs** `terraform apply` — fingerprint unlocks the approved plan.

## Async approval (no terminal polling)

When blocked, the terminal exits immediately:

```
[pilot-rail] BLOCKED — approval required.
  Request ID: 1777291e...
  Approver notified (mock: #security-approvals)
  Re-run `terraform apply` after approval.
```

After approval, re-running `terraform apply` with the same code unlocks via plan fingerprint.

## Live demo

```bash
cd demo-workspace
terraform init

# Scene 1: safe change (auto-approved)
cp scenarios/safe_marketing_readonly.tf main.tf
terraform apply

# Scene 2: risky change (blocked — fail fast)
cp scenarios/risky_contractor_admin.tf main.tf
terraform apply   # exits immediately with request ID
# Approve in dashboard → Notifications tab → re-run terraform apply
```

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PILOT_API_BASE` | `http://127.0.0.1:8000/api` | Pilot Rail API |
| `PILOT_REAL_TERRAFORM` | `backend/bin/terraform` | Path to real terraform binary |
