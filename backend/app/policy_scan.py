from app.models import PilotGuidance, PlanState, PolicyFinding, ScanResult
from app.policy_ai import _fallback_guidance, review_with_ai
from app.policy_engine import scan_with_rules

SEVERITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1}


def _highest_severity(findings: list[PolicyFinding]) -> str:
    if not findings:
        return "none"
    return max(findings, key=lambda f: SEVERITY_ORDER.get(f.severity, 0)).severity


def _route(risk_tier: str) -> tuple[str, PlanState]:
    if risk_tier == "critical":
        return "mandatory", PlanState.PENDING_REVIEW
    if risk_tier == "high":
        return "soft_mandatory", PlanState.PENDING_REVIEW
    return "advisory", PlanState.AUTO_APPROVED


def scan_plan(
    code: str,
    prompt: str,
    plan_json: str | None = None,
    skip_ai: bool = False,
) -> ScanResult:
    """
    Two-tier policy scan with risk-based routing:
    1. Deterministic rule engine (always)
    2. LLM reviewer (optional, skipped for fast wrapper path)
    """
    scan_text = code
    if plan_json:
        scan_text = f"{code}\n{plan_json}"

    rule_findings = scan_with_rules(scan_text)

    if skip_ai:
        guidance = _fallback_guidance(rule_findings)
        scan_model = "rule_engine_only"
        ai_findings: list[PolicyFinding] = []
    else:
        ai_findings, guidance, scan_model = review_with_ai(code, prompt, rule_findings)
        if scan_model == "none" and not guidance.message:
            guidance = _fallback_guidance(rule_findings)

    all_findings = rule_findings + ai_findings
    risk_tier = _highest_severity(all_findings)
    enforcement_level, recommended_state = _route(risk_tier)

    if recommended_state == PlanState.AUTO_APPROVED and not all_findings:
        guidance = PilotGuidance(
            message="No policy gaps detected. Change auto-approved by policy engine.",
            suggestion="Proceeding with terraform apply.",
        )

    return ScanResult(
        findings=all_findings,
        security_warning=len(all_findings) > 0,
        pilot_guidance=guidance,
        scan_model=scan_model,
        risk_tier=risk_tier,
        enforcement_level=enforcement_level,
        recommended_state=recommended_state,
    )
