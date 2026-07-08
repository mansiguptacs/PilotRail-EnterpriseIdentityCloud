# Pilot Rail Mini

A hackathon MVP demonstrating **transparent apply-gate governance** for AI-generated infrastructure and IAM/access changes — the core interaction pattern behind Saviynt's AI Onboarding Platform.

## What It Demonstrates

| JD Concept | Implementation |
|---|---|
| **Pilot Rail** (HITL approval interface) | Web dashboard for security reviewers + terraform apply gate |
| **Plan state machine** | `PENDING_REVIEW → APPROVED / REJECTED` + `AUTO_APPROVED` for low-risk |
| **Risk-based routing** | Critical/high → human review; clean → auto-approved (Sentinel-style) |
| **IaC template generation** | LangChain + OpenAI (UI path) or real terraform plan (wrapper path) |
| **Policy gap reporting** | YAML rule engine (AWS + IAM baselines) + optional AI reviewer |
| **Signed context packet** | SHA-256 integrity hash over plan metadata |
| **Audit log service** | AUTO_APPROVE, APPROVE, REJECT, EXECUTE with named actors |
| **Pilot agent panel** | Contextual guidance based on enforcement level |
| **Connector health APIs** | Live checks: OpenAI, Terraform CLI, Registry, policy engine |
| **Separation of duties** | Approver cannot equal requester (409 enforced) |

## Architecture

```
Developer/Cursor Agent → terraform apply (wrapper shim on PATH)
                              ↓
                    real terraform plan + show -json
                              ↓
                    Pilot Rail policy engine (risk route)
                              ↓
              AUTO_APPROVED ──────────→ real terraform apply
              PENDING_REVIEW → fail fast + notify approver
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

### 3. Terraform apply gate

```bash
bash scripts/install-terraform.sh
export PATH="$(pwd)/cli/shim:$PATH"
export PILOT_REAL_TERRAFORM="$(pwd)/backend/bin/terraform"
```

### 4. Demo workspace

Open `demo-workspace/` as a separate Cursor window (the "customer" repo).

```bash
cd demo-workspace
terraform init
terraform apply    # gated by Pilot Rail shim
```

## Live Demo Script (for interview)

**Setup:** Backend on :8000, frontend on :5173, shim on PATH. Two windows: Cursor (demo-workspace) + browser (dashboard).

### Scene 1 — Auto-approved (gate isn't ceremonial)
```bash
cd demo-workspace
cp scenarios/safe_marketing_readonly.tf main.tf
terraform apply
```
Low risk → auto-approved → apply succeeds. Dashboard shows AUTO_APPROVED entry.

### Scene 2 — Blocked (fail-fast, async approval)
```bash
cp scenarios/risky_contractor_admin.tf main.tf
terraform apply   # fails immediately with request ID
```
Dashboard Notifications tab shows approver alert. Admin approves as SEC.
Dev re-runs `terraform apply` → fingerprint unlock → apply proceeds.

### Scene 3 — Approve + audit
```bash
cp scenarios/scoped_contractor.tf main.tf
terraform apply
```
Admin approves → apply proceeds. Audit log shows AUTO_APPROVE, REJECT, APPROVE, EXECUTE entries.

### Talk track
- "The dev's terminal never blocks — fail-fast is how CI gates and PAM brokers work"
- "Approvers work from a queue with notifications, not a live terminal"
- "Re-run after approval matches Terraform Cloud confirmed apply and Saviynt JIT"

## Project Structure

```
├── backend/           # FastAPI + policy engine
├── frontend/          # React reviewer dashboard
├── cli/shim/terraform # Apply gate wrapper (put on PATH)
├── demo-workspace/    # Customer Terraform repo for live demo
├── scripts/           # install-terraform.sh
└── cli/README.md      # Shim setup and demo commands
```
