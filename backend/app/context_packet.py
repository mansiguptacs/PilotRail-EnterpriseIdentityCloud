import hashlib
import json
from datetime import datetime, timezone

from app.models import ContextPacket, Plan, PlanState, PolicyFinding


def _canonical_json(data: dict) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def build_context_packet(
    plan_id: str,
    prompt: str,
    model: str,
    reasoning: str,
    findings: list[PolicyFinding],
    state: PlanState,
    created_at: str,
) -> ContextPacket:
    payload = {
        "plan_id": plan_id,
        "prompt": prompt,
        "model": model,
        "reasoning": reasoning,
        "findings": [f.model_dump() for f in findings],
        "state": state.value,
        "created_at": created_at,
    }
    integrity_hash = hashlib.sha256(_canonical_json(payload).encode()).hexdigest()
    return ContextPacket(
        plan_id=plan_id,
        prompt=prompt,
        model=model,
        reasoning=reasoning,
        findings=findings,
        state=state,
        created_at=created_at,
        integrity_hash=integrity_hash,
    )


def build_packet_for_plan(plan: Plan) -> ContextPacket:
    return build_context_packet(
        plan_id=plan.id,
        prompt=plan.prompt,
        model=plan.model,
        reasoning=plan.reasoning,
        findings=plan.findings,
        state=plan.state,
        created_at=plan.created_at,
    )


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
