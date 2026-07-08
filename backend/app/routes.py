import os

from fastapi import APIRouter, HTTPException

from app.ai_layer import generate_plan
from app.connector_health import get_all_connector_health
from app.fingerprint import compute_plan_fingerprint
from app.models import (
    ApproveRequest,
    ConnectorHealth,
    CreatePlanRequest,
    ExecutionReport,
    Notification,
    Plan,
    PlanState,
    RejectRequest,
    ResetDemoRequest,
    ResetDemoResponse,
)
from app.notifications import (
    notify_approver,
    notify_requester_approved,
    notify_requester_rejected,
)
from app.policy_scan import scan_plan
from app.store import (
    append_audit,
    create_plan,
    find_plan_by_fingerprint,
    get_plan,
    list_audit_entries,
    list_notifications,
    list_plans,
    record_execution,
    reset_demo_data,
    transition_plan,
)

router = APIRouter(prefix="/api")


def _normalize_identity(name: str) -> str:
    return name.strip().lower()


def _skip_ai_for_source(source: str) -> bool:
    if source != "wrapper":
        return False
    return os.getenv("PILOT_AI_ON_APPLY", "true").strip().lower() in ("0", "false", "no")


@router.post("/plans", response_model=Plan)
def create_plan_endpoint(body: CreatePlanRequest) -> Plan:
    skip_ai = _skip_ai_for_source(body.source)

    if body.code:
        prompt = body.prompt or f"terraform apply by {body.requester}"
        code = body.code
        reasoning = "Submitted from terraform wrapper shim (plan evaluated at apply gate)"
        model = "wrapper-submission"
        fingerprint = compute_plan_fingerprint(
            code, body.plan_json, body.workspace_path, body.requester
        )

        existing = find_plan_by_fingerprint(
            fingerprint,
            body.requester,
            code=code,
            workspace_path=body.workspace_path,
        )
        scan = None
        if existing:
            if existing.state == PlanState.APPROVED:
                return existing
            if existing.state == PlanState.REJECTED:
                return existing
            if existing.state == PlanState.PENDING_REVIEW:
                return existing
            if existing.state == PlanState.AUTO_APPROVED:
                scan = scan_plan(code, prompt, body.plan_json, skip_ai=skip_ai)
                if scan.recommended_state == PlanState.AUTO_APPROVED:
                    return existing

        if scan is None:
            scan = scan_plan(code, prompt, body.plan_json, skip_ai=skip_ai)
    else:
        generated = generate_plan(body.prompt)  # type: ignore[arg-type]
        code = generated["code"]
        reasoning = generated["reasoning"]
        model = generated["model"]
        scan = scan_plan(code, body.prompt, skip_ai=False)  # type: ignore[arg-type]
        prompt = body.prompt  # type: ignore[assignment]
        fingerprint = compute_plan_fingerprint(code, body.plan_json, body.workspace_path, body.requester)

    plan = create_plan(
        prompt=prompt,
        code=code,
        reasoning=reasoning,
        model=model,
        security_warning=scan.security_warning,
        findings=scan.findings,
        state=scan.recommended_state,
        requester=body.requester,
        source=body.source,
        risk_tier=scan.risk_tier,
        enforcement_level=scan.enforcement_level,
        pilot_guidance=scan.pilot_guidance,
        scan_model=scan.scan_model,
        plan_fingerprint=fingerprint,
        workspace_path=body.workspace_path,
    )

    if plan.state == PlanState.AUTO_APPROVED:
        append_audit(
            plan_id=plan.id,
            action="AUTO_APPROVE",
            reviewer_initials="policy-engine",
            previous_state=PlanState.PENDING_REVIEW,
            new_state=PlanState.AUTO_APPROVED,
            comment="No critical/high policy violations detected",
        )
    elif plan.state == PlanState.PENDING_REVIEW:
        append_audit(
            plan_id=plan.id,
            action="NOTIFY_APPROVER",
            reviewer_initials="policy-engine",
            previous_state=PlanState.PENDING_REVIEW,
            new_state=PlanState.PENDING_REVIEW,
            comment="Approver notified via mock notification channel",
        )
        notify_approver(plan)

    return plan


@router.get("/plans", response_model=list[Plan])
def list_plans_endpoint() -> list[Plan]:
    return list_plans()


@router.get("/plans/{plan_id}", response_model=Plan)
def get_plan_endpoint(plan_id: str) -> Plan:
    plan = get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@router.post("/plans/{plan_id}/approve", response_model=Plan)
def approve_plan_endpoint(plan_id: str, body: ApproveRequest) -> Plan:
    plan = get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    if _normalize_identity(body.reviewer_initials) == _normalize_identity(plan.requester):
        raise HTTPException(
            status_code=409,
            detail="Separation of duties: approver cannot be the same as requester",
        )
    try:
        updated = transition_plan(
            plan_id=plan_id,
            new_state=PlanState.APPROVED,
            reviewer_initials=body.reviewer_initials,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    append_audit(
        plan_id=plan_id,
        action="APPROVE",
        reviewer_initials=body.reviewer_initials,
        previous_state=PlanState.PENDING_REVIEW,
        new_state=PlanState.APPROVED,
    )
    notify_requester_approved(updated, body.reviewer_initials)
    return updated


@router.post("/plans/{plan_id}/reject", response_model=Plan)
def reject_plan_endpoint(plan_id: str, body: RejectRequest) -> Plan:
    plan = get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    if _normalize_identity(body.reviewer_initials) == _normalize_identity(plan.requester):
        raise HTTPException(
            status_code=409,
            detail="Separation of duties: reviewer cannot be the same as requester",
        )
    try:
        updated = transition_plan(
            plan_id=plan_id,
            new_state=PlanState.REJECTED,
            reviewer_initials=body.reviewer_initials,
            reject_comment=body.comment,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    append_audit(
        plan_id=plan_id,
        action="REJECT",
        reviewer_initials=body.reviewer_initials,
        previous_state=PlanState.PENDING_REVIEW,
        new_state=PlanState.REJECTED,
        comment=body.comment,
    )
    notify_requester_rejected(updated, body.reviewer_initials, body.comment)
    return updated


@router.post("/plans/{plan_id}/execution", response_model=Plan)
def report_execution_endpoint(plan_id: str, body: ExecutionReport) -> Plan:
    plan = get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    if plan.state not in (PlanState.APPROVED, PlanState.AUTO_APPROVED):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot record execution for plan in state {plan.state.value}",
        )
    updated = record_execution(
        plan_id=plan_id,
        status=body.status,
        output=body.output,
        exit_code=body.exit_code,
    )
    append_audit(
        plan_id=plan_id,
        action="EXECUTE",
        reviewer_initials=plan.requester,
        previous_state=plan.state,
        new_state=plan.state,
        comment=f"exit_code={body.exit_code}",
    )
    return updated


@router.get("/audit")
def get_audit_log():
    return list_audit_entries()


@router.get("/notifications", response_model=list[Notification])
def get_notifications(recipient: str | None = None) -> list[Notification]:
    return list_notifications(recipient)


@router.get("/connectors/health", response_model=list[ConnectorHealth])
def get_connector_health() -> list[ConnectorHealth]:
    return get_all_connector_health()


@router.post("/admin/reset-demo", response_model=ResetDemoResponse)
def reset_demo_endpoint(body: ResetDemoRequest) -> ResetDemoResponse:
    counts = reset_demo_data(clear_workstations=body.clear_workstations)
    return ResetDemoResponse(
        message=f"Demo data reset by {body.reviewer_initials}",
        plans_cleared=counts["plans_cleared"],
        audit_cleared=counts["audit_cleared"],
        notifications_cleared=counts["notifications_cleared"],
        workstations_cleared=counts.get("workstations_cleared", 0),
        workstation_notifications_cleared=counts.get("workstation_notifications_cleared", 0),
    )
