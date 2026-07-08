# Cloud Access Repository

Internal Terraform repo for IAM/access policy changes. All `terraform apply`
commands are governed by the platform team's terraform tooling (Pilot Rail apply gate).

## Baseline state

`main.tf` defines the current sanctioned least-privilege grant for the marketing
service (read-only access to the reports bucket).

## Deploy changes

**Important:** Enable the Pilot Rail apply gate first (from repo root):

```bash
source ../scripts/enable-gate.sh
```

Then deploy:

```bash
terraform init
terraform apply
```

Do **not** run `backend/bin/terraform apply` directly — that bypasses the gate.
You should see a blue `PILOT RAIL APPLY GATE` banner when apply is intercepted.

## Demo scenarios

Fallback snippets in `scenarios/` if you need deterministic content:

| File | Risk | Expected gate |
|------|------|---------------|
| `safe_marketing_readonly.tf` | Low | Auto-approved |
| `risky_contractor_admin.tf` | Critical | Blocked — fail fast, re-run after approval |
| `scoped_contractor.tf` | Medium | May require review |

To try a scenario, replace `main.tf` content with the scenario file, then run `terraform apply`.

For blocked scenarios: apply fails immediately. After approval in the dashboard, re-run `terraform apply` with the same code.
