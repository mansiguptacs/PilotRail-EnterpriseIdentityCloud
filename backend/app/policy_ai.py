import json
import os
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.models import PilotGuidance, PolicyFinding

REVIEW_SYSTEM_PROMPT = """You are a cloud security policy reviewer for an enterprise IaC governance platform.
Analyze Terraform HCL against AWS security best practices and CIS benchmarks.

You will receive:
1. The original user request
2. Generated Terraform code
3. Findings already detected by the deterministic rule engine

Your job:
- Identify ADDITIONAL policy gaps the rule engine may have missed (semantic issues, missing controls, privilege escalation)
- Do NOT duplicate findings already listed
- Provide actionable pilot guidance for the human reviewer

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
    "suggestion": "specific recommended action (approve with caution, reject, request revision)"
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


def review_with_ai(
    code: str,
    prompt: str,
    rule_findings: list[PolicyFinding],
) -> tuple[list[PolicyFinding], PilotGuidance, str]:
    """LLM policy review pass — catches semantic gaps rules miss."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return [], _fallback_guidance(rule_findings), "none"

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=api_key)
    user_content = f"""Original request: {prompt}

Terraform code:
```
{code}
```

Rule engine findings (do not duplicate these):
{_format_existing_findings(rule_findings)}
"""

    response = llm.invoke(
        [
            SystemMessage(content=REVIEW_SYSTEM_PROMPT),
            HumanMessage(content=user_content),
        ]
    )
    parsed = _parse_review_response(response.content)

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
    )
    return ai_findings, guidance, "gpt-4o-mini"


def _fallback_guidance(findings: list[PolicyFinding]) -> PilotGuidance:
    """Deterministic guidance when OpenAI is unavailable."""
    if not findings:
        return PilotGuidance(
            message="No policy gaps detected by the rule engine. Review the generated code to confirm it matches the original request.",
            suggestion="Type your initials to confirm you have reviewed the plan before approving.",
        )

    critical = [f for f in findings if f.severity == "critical"]
    if critical:
        return PilotGuidance(
            message=f"Rule engine flagged {len(critical)} critical violation(s) including {critical[0].term}. These configurations could expose infrastructure to unauthorized access.",
            suggestion="Reject this plan and request a revision that addresses the flagged policy gaps.",
        )

    return PilotGuidance(
        message=f"Rule engine detected {len(findings)} policy gap(s). Review each finding and verify the configuration aligns with your security baseline.",
        suggestion="Check whether the flagged settings are intentional before approving.",
    )
