# Pilot Rail Mini

A hackathon MVP demonstrating **transparent apply-gate governance** for AI-generated infrastructure and IAM/access changes — the core interaction pattern behind Saviynt's AI Onboarding Platform.

## What It Demonstrates

| JD Concept | Implementation |
|---|---|
| **Pilot Rail** (HITL approval interface) | Web dashboard for security reviewers + terraform apply gate |
| **Plan state machine** | `PENDING_REVIEW → APPROVED / REJECTED` + `AUTO_APPROVED` for low-risk |
| **Risk-based routing** | Critical/high → human review; clean → auto-approved (Sentinel-style) |
| **Async approval flow** | Fail-fast on block; no terminal polling; dev re-runs apply after decision |
| **Plan fingerprint unlock** | SHA-256 envelope over code + plan intent; re-apply unlocks prior approval |
| **Mock notifications** | Approver/requester alerts in dashboard feed (Slack-style, no real integration) |
| **IaC template generation** | LangChain + OpenAI (UI path) or real terraform plan (wrapper path) |
| **Policy gap reporting** | YAML rule engine (AWS + IAM baselines) + optional AI reviewer |
| **Signed context packet** | SHA-256 integrity hash over plan metadata |
| **Audit log service** | AUTO_APPROVE, APPROVE, REJECT, EXECUTE, NOTIFY_* with named actors |
| **Pilot agent panel** | Contextual guidance based on enforcement level |
| **Connector health APIs** | Live checks: OpenAI, Terraform CLI, Registry, policy engine |
| **Separation of duties** | Approver cannot equal requester (409 enforced) |

## Architecture

```
Developer/Cursor Agent → terraform apply (wrapper shim on PATH)
                              ↓
                    real terraform plan + show -json
                              ↓
                    compute plan fingerprint (code + resource changes)
                              ↓
                    Pilot Rail policy engine (risk route)
                              ↓
              AUTO_APPROVED ──────────→ real terraform apply
              PENDING_REVIEW → fail fast (exit 1) + notify approver
                              ↓
                    Admin dashboard → approve/reject → notify requester
                              ↓
                    Dev re-runs apply → fingerprint unlock → apply proceeds
```

## Quick Start

### 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt   # or: uv pip install -r requirements.txt
cp .env.example .env              # add OPENAI_API_KEY for AI features
uvicorn app.main:app --reload
```

### 2. Frontend

```bash
cd frontend && npm install && npm run dev
```

Open the reviewer dashboard at http://127.0.0.1:5173

### 3. Terraform apply gate

```bash
# From repo root — one-time install
bash scripts/install-terraform.sh

# Every new terminal session (required)
source scripts/enable-gate.sh
```

`enable-gate.sh` puts the shim first on `PATH`, points at the real terraform binary, and verifies the backend is reachable. Do **not** run `backend/bin/terraform apply` directly — that bypasses the gate.

### 4. Demo workspace

Open `demo-workspace/` as a separate Cursor window (the "customer" repo).

```bash
source scripts/enable-gate.sh   # from repo root, once per terminal
cd demo-workspace
terraform init
terraform apply                 # gated by Pilot Rail shim
```

## Async Approval Flow

When a change is blocked, the terminal **never waits** for a human:

1. Shim submits plan + fingerprint to `POST /api/plans`
2. Backend routes critical/high risk to `PENDING_REVIEW` and notifies approvers
3. Shim prints request ID and exits immediately (`exit 1`)
4. Admin reviews in dashboard (Notifications tab + plan queue)
5. On approve/reject, requester is notified to re-run apply
6. Dev runs `terraform apply` again with the same code
7. Fingerprint matches the prior decision → unlock (no new review needed)

Rejected plans fail fast on re-apply with the reviewer's reason. Approved plans proceed to real `terraform apply`.

## Live Demo Script (for interview)

**Setup:** Backend on :8000, frontend on :5173, gate enabled via `source scripts/enable-gate.sh`. Two windows: Cursor (`demo-workspace`) + browser (dashboard at :5173).

**Reviewer tip:** Approve as `SEC` (or any initials **different from your git user name**). The shim sets the requester from `git config user.name` — separation of duties blocks self-approval.

### Scene 1 — Auto-approved (gate isn't ceremonial)

```bash
source scripts/enable-gate.sh
cd demo-workspace
cp scenarios/safe_marketing_readonly.tf main.tf
terraform apply
```

Low risk → auto-approved → apply succeeds. Dashboard shows `AUTO_APPROVED` entry.

### Scene 2 — Blocked (fail-fast, async approval)

```bash
cp scenarios/risky_contractor_admin.tf main.tf
terraform apply   # fails immediately with request ID
```

- Terminal exits immediately — no polling
- Dashboard **Notifications** tab shows approver alert
- Admin approves as `SEC` in the Pilot Rail dashboard
- Dashboard shows requester notification: re-run apply
- Dev re-runs `terraform apply` → fingerprint unlock → apply proceeds

Shortcut: `bash scripts/demo-risky.sh` runs step 1 and prints the remaining steps.

### Scene 3 — Scoped change + audit trail

```bash
cp scenarios/scoped_contractor.tf main.tf
terraform apply
```

Approve if routed to review. Audit log shows `AUTO_APPROVE`, `NOTIFY_APPROVER`, `APPROVE`, `REJECT`, and `EXECUTE` entries with named actors.

### Talk track

- "The dev's terminal never blocks — fail-fast is how CI gates and PAM brokers work"
- "Approvers work from a queue with notifications, not a live terminal"
- "Re-run after approval matches Terraform Cloud confirmed apply and Saviynt JIT credential release"
- "Plan fingerprint is the approval envelope — same code unlocks without a second review"

## Project Structure

```
├── backend/              # FastAPI + policy engine + notifications
│   ├── app/              # routes, store, fingerprint, policy_scan, ...
│   └── policies/         # aws_baseline.yaml, iam_baseline.yaml
├── frontend/             # React reviewer dashboard (queue, notifications, audit)
├── cli/shim/terraform    # Apply gate wrapper (put on PATH via enable-gate.sh)
├── demo-workspace/       # Customer Terraform repo for live demo
├── scripts/
│   ├── install-terraform.sh  # Download terraform to backend/bin/
│   ├── enable-gate.sh        # Enable shim + verify backend (source this)
│   └── demo-risky.sh         # Fail-fast risky scenario helper
└── cli/README.md         # Shim setup, env vars, and demo commands
```

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/plans` | Submit plan; fingerprint unlock for prior approvals |
| `GET` | `/api/plans` | List plan queue |
| `POST` | `/api/plans/{id}/approve` | Approve (separation of duties enforced) |
| `POST` | `/api/plans/{id}/reject` | Reject with comment |
| `GET` | `/api/notifications` | Mock notification feed |
| `GET` | `/api/audit` | Audit log |
| `GET` | `/api/connectors/health` | Connector health strip |
