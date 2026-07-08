import type { Plan } from "../types";
import "./PilotAgentPanel.css";

interface Props {
  plan: Plan;
}

function dispositionGuidance(plan: Plan): { message: string; suggestion: string } | null {
  if (plan.state === "AUTO_APPROVED") {
    return {
      message: "Policy engine found no critical or high-severity violations. Change auto-approved.",
      suggestion: "Terraform apply proceeded without human review (advisory enforcement).",
    };
  }
  if (plan.state === "APPROVED") {
    return {
      message: `Plan approved by ${plan.reviewer_initials}. Terraform apply may proceed.`,
      suggestion: "",
    };
  }
  if (plan.state === "REJECTED") {
    return {
      message: `Plan rejected by ${plan.reviewer_initials}: "${plan.reject_comment}"`,
      suggestion: "The developer's terraform apply command will fail with this reason.",
    };
  }
  if (plan.enforcement_level === "mandatory") {
    return {
      message: `Critical risk detected (${plan.risk_tier}). Mandatory override required before apply can proceed.`,
      suggestion: "Reject unless there is an explicit business justification and compensating controls.",
    };
  }
  if (plan.enforcement_level === "soft_mandatory") {
    return {
      message: `High-risk change from ${plan.requester}. Review policy findings before approving.`,
      suggestion: "Verify least-privilege alternatives exist before granting approval.",
    };
  }
  return null;
}

export default function PilotAgentPanel({ plan }: Props) {
  const disposition = dispositionGuidance(plan);
  const guidance = disposition ?? plan.pilot_guidance;
  const isAiGuidance = !disposition && plan.scan_model !== "none" && plan.scan_model !== "rule_engine_only";

  return (
    <div className="pilot-panel">
      <div className="pilot-panel-header">
        <span className="icon">&#9992;</span>
        <h4>Pilot Agent {isAiGuidance && <span className="ai-badge">AI</span>}</h4>
      </div>
      <p>{guidance.message}</p>
      {guidance.suggestion && <p className="suggestion">{guidance.suggestion}</p>}
      {plan.pilot_guidance.developer_hint && (
        <div className="developer-hint">
          <strong>Developer coach</strong>
          <pre>{plan.pilot_guidance.developer_hint}</pre>
        </div>
      )}
    </div>
  );
}
