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
| **IaC template generation** | LangChain + Grok/xAI (UI path) or real terraform plan (wrapper path) |
| **Policy gap reporting** | YAML rule engine (AWS + IAM baselines) + Grok reviewer on apply and UI paths |
| **Developer coach** | AI-generated fix steps shown in terminal when apply is blocked + in dashboard |
| **Signed context packet** | SHA-256 integrity hash over plan metadata |
| **Audit log service** | AUTO_APPROVE, APPROVE, REJECT, EXECUTE, NOTIFY_* with named actors |
| **Pilot agent panel** | Contextual guidance based on enforcement level |
| **Connector health APIs** | Live checks for infra; Grok status from config + last policy scan (no idle API probes) |
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
cp .env.example .env              # add XAI_API_KEY from https://console.x.ai
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

## Enterprise Container Demo (IT agent push)

Simulate a managed developer environment with Docker — portable on Mac M3, Linux, or any machine with Docker.

### Setup

**Quick start (one command — all services in Docker):**

```bash
bash scripts/demo-start.sh
```

Starts **backend** (`:8000`), **frontend** (`:5173`), and **pilot-dev** workstation via Docker Compose. No local Python venv or npm install required.

**Interview IT-push story (infra only — you click Deploy Gate):**

```bash
bash scripts/demo-start.sh --no-push
```

`demo-stop.sh` runs `docker compose down` to stop everything.

**Manual compose (equivalent):**

```bash
bash scripts/provision-dev-container.sh   # build + up all services
bash scripts/demo-preflight.sh
```

### Container operations

```bash
bash scripts/container-ops.sh start      # start pilot-dev
bash scripts/container-ops.sh shell      # developer terminal
bash scripts/container-ops.sh agent-log  # tail IT deploy notifications
bash scripts/container-ops.sh status     # container + SSH port 2222
```

### Discovery

Workstations on the **shared network** are discovered without orchestrator/Docker API access:

1. **Self-registration** — developer pod beacons `POST /api/workstations/register` on startup
2. **Network probe** — admin pod TCP-checks known hostnames (`PILOT_KNOWN_WORKSTATIONS`, default `pilot-dev:22`)
3. **Agent heartbeat** — runtime ONLINE/STALE/OFFLINE after IT deploy

IT push uses **SSH over the internal network** (`developer@pilot-dev:22`), not `docker exec`. Port `2222` on the host is only for manual/debug SSH from your laptop.

### Interview flow (two panes)

| Pane | Content |
|------|---------|
| Browser | Workstations tab — fleet view + one-click Deploy Gate |
| Terminal | `bash scripts/container-ops.sh shell` + optional `agent-log` |

**Scene A — IT pushes agent**
1. Workstations tab shows discovered `pilot-dev` container (NOT_DEPLOYED)
2. Click **Deploy Gate** (one click) as SEC
3. Container shows notification in agent log + shell banner
4. `which terraform` → `~/.pilot-rail/shim/terraform`

**Scene B — Terraform intercept**
1. In container: `cd ~/demo-workspace && cp scenarios/risky_contractor_admin.tf main.tf`
2. `terraform apply` → fail fast → approve in dashboard → re-run apply

**Talk track:** "Security pushes the sanctioned apply gate into the managed dev container — same pattern as platform-mandated dev environments."

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
├── demo-container/       # Ubuntu dev workstation image (sshd + beacon)
├── docker-compose.yml    # backend + frontend + pilot-dev workstation
├── backend/Dockerfile    # FastAPI control plane image
├── frontend/Dockerfile   # Vite dashboard image
├── scripts/
│   ├── install-terraform.sh       # Download terraform to backend/bin/
│   ├── enable-gate.sh             # Enable shim + verify backend (source this)
│   ├── provision-dev-container.sh # Build + start pilot-dev container
│   ├── demo-start.sh              # One-command demo bootstrap
│   ├── demo-stop.sh               # Stop background demo services
│   ├── container-ops.sh           # start/stop/shell/agent-log/status
│   ├── demo-preflight.sh          # Portable demo readiness checks
│   └── demo-risky.sh              # Fail-fast risky scenario helper
├── cli/agent/                # pilot-rail-agent, remote-install.sh
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
| `GET` | `/api/workstations` | Fleet list with agent status |
| `GET` | `/api/workstations/discover` | Discover managed Docker workstations |
| `POST` | `/api/workstations/register` | Container self-registration beacon |
| `POST` | `/api/workstations/push` | IT admin one-click shim deploy |
| `POST` | `/api/workstations/{id}/heartbeat` | Agent heartbeat |
| `POST` | `/api/workstations/{id}/revoke` | Revoke gate on workstation |
| `GET` | `/api/audit` | Audit log |
| `GET` | `/api/connectors/health` | Connector health strip |
