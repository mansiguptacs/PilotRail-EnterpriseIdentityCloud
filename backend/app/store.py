import json
import uuid
from pathlib import Path
from typing import Optional

from app.context_packet import build_context_packet, utc_now
from app.fingerprint import compute_code_fingerprint
from app.models import AuditEntry, Notification, Plan, PlanState, PilotGuidance

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PLANS_FILE = DATA_DIR / "plans.json"
AUDIT_FILE = DATA_DIR / "audit_log.json"
NOTIFICATIONS_FILE = DATA_DIR / "notifications.json"


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path, default: list) -> list:
    _ensure_data_dir()
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data: list) -> None:
    _ensure_data_dir()
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def list_plans() -> list[Plan]:
    raw = _read_json(PLANS_FILE, [])
    plans = []
    for item in raw:
        try:
            plans.append(Plan.model_validate(item))
        except Exception:
            continue
    return plans


def get_plan(plan_id: str) -> Optional[Plan]:
    for plan in list_plans():
        if plan.id == plan_id:
            return plan
    return None


_STATE_PRIORITY = {
    PlanState.APPROVED: 0,
    PlanState.AUTO_APPROVED: 0,
    PlanState.PENDING_REVIEW: 1,
    PlanState.REJECTED: 2,
}


def _pick_best_plan(candidates: list[Plan]) -> Optional[Plan]:
    if not candidates:
        return None
    return min(candidates, key=lambda p: _STATE_PRIORITY.get(p.state, 99))


def find_plan_by_fingerprint(
    fingerprint: str,
    requester: str,
    code: str | None = None,
    workspace_path: str | None = None,
) -> Optional[Plan]:
    if not fingerprint and not code:
        return None
    requester_norm = requester.strip().lower()
    plans = list_plans()
    fingerprint_matches: list[Plan] = []
    legacy_matches: list[Plan] = []
    code_hash = compute_code_fingerprint(code) if code else None

    for plan in plans:
        if plan.requester.strip().lower() != requester_norm:
            continue
        if fingerprint and plan.plan_fingerprint == fingerprint:
            fingerprint_matches.append(plan)
            continue
        if (
            code_hash
            and workspace_path
            and plan.workspace_path == workspace_path
            and compute_code_fingerprint(plan.code) == code_hash
        ):
            legacy_matches.append(plan)

    return _pick_best_plan(fingerprint_matches) or _pick_best_plan(legacy_matches)


def create_plan(
    prompt: str,
    code: str,
    reasoning: str,
    model: str,
    security_warning: bool,
    findings: list,
    state: PlanState,
    requester: str = "unknown",
    source: str = "ui",
    risk_tier: str = "none",
    enforcement_level: str = "advisory",
    pilot_guidance=None,
    scan_model: str = "none",
    plan_fingerprint: str = "",
    workspace_path: str = "",
) -> Plan:
    now = utc_now()
    plan_id = str(uuid.uuid4())
    packet = build_context_packet(
        plan_id=plan_id,
        prompt=prompt,
        model=model,
        reasoning=reasoning,
        findings=findings,
        state=state,
        created_at=now,
    )
    if pilot_guidance is None:
        pilot_guidance = PilotGuidance(message="")
    plan = Plan(
        id=plan_id,
        prompt=prompt,
        code=code,
        reasoning=reasoning,
        state=state,
        security_warning=security_warning,
        findings=findings,
        model=model,
        scan_model=scan_model,
        pilot_guidance=pilot_guidance,
        requester=requester,
        source=source,
        risk_tier=risk_tier,
        enforcement_level=enforcement_level,
        plan_fingerprint=plan_fingerprint,
        workspace_path=workspace_path,
        context_packet_hash=packet.integrity_hash,
        created_at=now,
        updated_at=now,
    )
    plans = list_plans()
    plans.insert(0, plan)
    _write_json(PLANS_FILE, [p.model_dump(mode="json") for p in plans])
    return plan


def transition_plan(
    plan_id: str,
    new_state: PlanState,
    reviewer_initials: str,
    reject_comment: Optional[str] = None,
) -> Plan:
    plans = list_plans()
    for i, plan in enumerate(plans):
        if plan.id != plan_id:
            continue
        if plan.state != PlanState.PENDING_REVIEW:
            raise ValueError(
                f"Cannot transition from {plan.state.value} to {new_state.value}"
            )
        updated = plan.model_copy(
            update={
                "state": new_state,
                "reviewer_initials": reviewer_initials,
                "reject_comment": reject_comment,
                "updated_at": utc_now(),
            }
        )
        plans[i] = updated
        _write_json(PLANS_FILE, [p.model_dump(mode="json") for p in plans])
        return updated
    raise KeyError(f"Plan {plan_id} not found")


def record_execution(
    plan_id: str,
    status: str,
    output: str,
    exit_code: int,
) -> Plan:
    plans = list_plans()
    for i, plan in enumerate(plans):
        if plan.id != plan_id:
            continue
        updated = plan.model_copy(
            update={
                "execution_status": status,
                "execution_output": output,
                "execution_exit_code": exit_code,
                "updated_at": utc_now(),
            }
        )
        plans[i] = updated
        _write_json(PLANS_FILE, [p.model_dump(mode="json") for p in plans])
        return updated
    raise KeyError(f"Plan {plan_id} not found")


def list_audit_entries() -> list[AuditEntry]:
    raw = _read_json(AUDIT_FILE, [])
    return [AuditEntry.model_validate(item) for item in raw]


def append_audit(
    plan_id: str,
    action: str,
    reviewer_initials: str,
    previous_state: PlanState,
    new_state: PlanState,
    comment: Optional[str] = None,
) -> AuditEntry:
    entry = AuditEntry(
        id=str(uuid.uuid4()),
        plan_id=plan_id,
        action=action,
        reviewer_initials=reviewer_initials,
        comment=comment,
        previous_state=previous_state,
        new_state=new_state,
        timestamp=utc_now(),
    )
    entries = list_audit_entries()
    entries.insert(0, entry)
    _write_json(AUDIT_FILE, [e.model_dump(mode="json") for e in entries])
    return entry


def save_notification(
    plan_id: str,
    recipient: str,
    channel: str,
    message: str,
    event_type: str,
) -> Notification:
    notification = Notification(
        id=str(uuid.uuid4()),
        plan_id=plan_id,
        recipient=recipient,
        channel=channel,
        message=message,
        event_type=event_type,
        timestamp=utc_now(),
    )
    entries = list_notifications()
    entries.insert(0, notification)
    _write_json(NOTIFICATIONS_FILE, [n.model_dump(mode="json") for n in entries])
    return notification


def list_notifications(recipient: Optional[str] = None) -> list[Notification]:
    raw = _read_json(NOTIFICATIONS_FILE, [])
    notifications = [Notification.model_validate(item) for item in raw]
    if recipient:
        recipient_norm = recipient.strip().lower()
        return [
            n
            for n in notifications
            if n.recipient.strip().lower() == recipient_norm
            or n.recipient == "#security-approvals"
            or n.recipient == "@security-team"
        ]
    return notifications
