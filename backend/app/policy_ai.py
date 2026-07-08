import json
import logging
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.grok_status import record_grok_failure, record_grok_success
from app.llm_client import get_chat_llm, model_label
from app.models import PilotGuidance, PolicyFinding

logger = logging.getLogger(__name__)

REVIEW_SYSTEM_PROMPT = """You are a cloud security policy reviewer for an enterprise IaC governance platform.
Analyze Terraform HCL against AWS security best practices and CIS benchmarks.

You will receive:
1. The original user request
2. Generated Terraform code
3. Findings already detected by the deterministic rule engine

Your job:
- Identify ADDITIONAL policy gaps the rule engine may have missed (semantic issues, missing controls, privilege escalation)
- Do NOT duplicate findings already listed
- Provide actionable pilot guidance for the human security reviewer
- Provide a concise, practical developer_hint: concrete Terraform edits the developer can make locally to fix the issues and re-run apply

Return ONLY valid JSON (no markdown):
{
  "additional_findings": [
    {
      "policy_id": "AI-001",
      "term": "short label",
      "line_number": 1,
      "severity": "critical|high|medium|low",
      "category": "network_exposure|data_exposure|identity_access|encryption|compliance",
      "message": "what is wrong",
      "remediation": "how to fix it",
      "matched_text": "relevant code snippet"
    }
  ],
  "pilot_guidance": {
    "message": "2-3 sentence summary for the human reviewer about overall risk",
    "suggestion": "specific recommended action (approve with caution, reject, request revision)",
    "developer_hint": "2-4 bullet steps for the developer to fix Terraform and retry apply. Reference file names and attributes. Be direct and actionable."
  }
}

If no additional findings, return empty additional_findings array.
Be precise. Reference actual line numbers from the code."""


def _parse_review_response(content: str) -> dict[str, Any]:
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\n?", "", content)
        content = re.sub(r"\n?```$", "", content)
    return json.loads(content)


def _format_existing_findings(findings: list[PolicyFinding]) -> str:
    if not findings:
        return "None"
    return "\n".join(
        f"- [{f.policy_id}] {f.term} (line {f.line_number}, {f.severity}): {f.message}"
        for f in findings
    )


def _ai_unavailable_note(exc: Exception) -> str:
    msg = str(exc).lower()
    if "quota" in msg or "429" in msg or "insufficient_quota" in msg or "credits" in msg:
        return (
            "Grok AI quota/billing exhausted for this API key "
            "— rule engine enforcement still active."
        )
    if "401" in msg or "invalid api key" in msg or "authentication" in msg:
        return "Grok API key invalid — rule engine enforcement still active."
    return "Grok AI review unavailable — rule engine enforcement still active."


def review_with_ai(
    code: str,
    prompt: str,
    rule_findings: list[PolicyFinding],
) -> tuple[list[PolicyFinding], PilotGuidance, str]:
    """LLM policy review pass — catches semantic gaps rules miss."""
    llm = get_chat_llm()
    if llm is None:
        return [], _fallback_guidance(rule_findings), "none"

    user_content = f"""Original request: {prompt}

Terraform code:
```
{code}
```

Rule engine findings (do not duplicate these):
{_format_existing_findings(rule_findings)}
"""

    try:
        response = llm.invoke(
            [
                SystemMessage(content=REVIEW_SYSTEM_PROMPT),
                HumanMessage(content=user_content),
            ]
        )
        parsed = _parse_review_response(response.content)
    except json.JSONDecodeError as exc:
        logger.warning("AI policy review returned invalid JSON: %s", exc)
        record_grok_failure("invalid JSON response")
        return [], _fallback_guidance(
            rule_findings,
            ai_note="Grok response could not be parsed — rule engine enforcement still active.",
        ), "ai_unavailable"
    except Exception as exc:
        logger.warning("AI policy review failed: %s", exc)
        record_grok_failure(str(exc))
        return [], _fallback_guidance(rule_findings, ai_note=_ai_unavailable_note(exc)), "ai_unavailable"

    ai_findings: list[PolicyFinding] = []
    for f in parsed.get("additional_findings", []):
        ai_findings.append(
            PolicyFinding(
                policy_id=f.get("policy_id", "AI-000"),
                term=f.get("term", "policy violation"),
                line_number=f.get("line_number", 0),
                severity=f.get("severity", "medium"),
                category=f.get("category", "compliance"),
                message=f.get("message", ""),
                remediation=f.get("remediation", ""),
                source="ai_reviewer",
                matched_text=f.get("matched_text", ""),
            )
        )

    guidance_data = parsed.get("pilot_guidance", {})
    guidance = PilotGuidance(
        message=guidance_data.get("message", ""),
        suggestion=guidance_data.get("suggestion", ""),
        developer_hint=guidance_data.get("developer_hint", ""),
    )
    if not guidance.developer_hint:
        guidance.developer_hint = _developer_hint_from_findings(rule_findings + ai_findings)
    record_grok_success()
    return ai_findings, guidance, model_label()


def _developer_hint_from_findings(findings: list[PolicyFinding]) -> str:
    if not findings:
        return ""
    lines = ["Before re-running terraform apply, address these policy gaps:"]
    for idx, finding in enumerate(findings[:5], start=1):
        fix = finding.remediation or finding.message
        lines.append(f"{idx}. [{finding.policy_id}] {fix}")
    if len(findings) > 5:
        lines.append(f"...and {len(findings) - 5} more finding(s) in the Pilot Rail dashboard.")
    return "\n".join(lines)


def _fallback_guidance(
    findings: list[PolicyFinding],
    ai_note: str = "",
) -> PilotGuidance:
    """Deterministic guidance when Grok AI is unavailable."""
    if not findings:
        message = "No policy gaps detected by the rule engine. Review the generated code to confirm it matches the original request."
        if ai_note:
            message = f"{ai_note} {message}"
        return PilotGuidance(
            message=message,
            suggestion="Type your initials to confirm you have reviewed the plan before approving.",
        )

    developer_hint = _developer_hint_from_findings(findings)
    if ai_note:
        developer_hint = f"{ai_note}\n\n{developer_hint}"

    critical = [f for f in findings if f.severity == "critical"]
    if critical:
        message = (
            f"Rule engine flagged {len(critical)} critical violation(s) including "
            f"{critical[0].term}. These configurations could expose infrastructure to unauthorized access."
        )
        if ai_note:
            message = f"{ai_note} {message}"
        return PilotGuidance(
            message=message,
            suggestion="Reject this plan and request a revision that addresses the flagged policy gaps.",
            developer_hint=developer_hint,
        )

    message = (
        f"Rule engine detected {len(findings)} policy gap(s). Review each finding and "
        "verify the configuration aligns with your security baseline."
    )
    if ai_note:
        message = f"{ai_note} {message}"
    return PilotGuidance(
        message=message,
        suggestion="Check whether the flagged settings are intentional before approving.",
        developer_hint=developer_hint,
    )
