import type { Plan } from "../types";
import { formatRelativeTime, shortId, workspaceLabel } from "../utils/format";
import Badge from "./ui/Badge";
import "./PlanHeader.css";

interface Props {
  plan: Plan;
}

function stateVariant(state: Plan["state"]): string {
  switch (state) {
    case "PENDING_REVIEW":
      return "pending";
    case "APPROVED":
      return "approved";
    case "REJECTED":
      return "rejected";
    case "AUTO_APPROVED":
      return "auto-approved";
  }
}

function stateLabel(state: Plan["state"]): string {
  switch (state) {
    case "PENDING_REVIEW":
      return "Pending review";
    case "APPROVED":
      return "Approved";
    case "REJECTED":
      return "Rejected";
    case "AUTO_APPROVED":
      return "Auto-approved";
  }
}

function dispositionLine(plan: Plan): string | null {
  if (plan.state === "APPROVED") {
    return `Approved by ${plan.reviewer_initials} — developer may re-run terraform apply.`;
  }
  if (plan.state === "REJECTED") {
    return `Rejected by ${plan.reviewer_initials}: ${plan.reject_comment ?? "No reason given"}`;
  }
  if (plan.state === "AUTO_APPROVED") {
    return "Auto-approved by policy engine — apply proceeded without human review.";
  }
  return null;
}

export default function PlanHeader({ plan }: Props) {
  const disposition = dispositionLine(plan);
  const ws = workspaceLabel(plan.workspace_path);
  const findingCount = plan.findings.length;
  const criticalCount = plan.findings.filter((f) => f.severity === "critical").length;

  return (
    <header className={`plan-header enforcement-${plan.enforcement_level}`}>
      <div className="plan-header-top">
        <Badge variant={stateVariant(plan.state)}>{stateLabel(plan.state)}</Badge>
        {plan.risk_tier !== "none" && (
          <Badge variant={plan.risk_tier}>{plan.risk_tier} risk</Badge>
        )}
        <Badge variant="neutral">{plan.enforcement_level.replace("_", " ")}</Badge>
        {plan.source === "wrapper" && <Badge variant="cli">CLI apply</Badge>}
      </div>

      <div className="plan-header-meta">
        <span>{plan.requester}</span>
        {ws && (
          <>
            <span className="sep">·</span>
            <span>{ws}</span>
          </>
        )}
        <span className="sep">·</span>
        <span title={plan.updated_at}>Updated {formatRelativeTime(plan.updated_at)}</span>
      </div>

      <div className="plan-header-ids">
        <span className="mono">Plan {shortId(plan.id)}</span>
        {plan.plan_fingerprint && (
          <>
            <span className="sep">·</span>
            <span className="mono" title={plan.plan_fingerprint}>
              fp {plan.plan_fingerprint.slice(0, 10)}…
            </span>
          </>
        )}
        {findingCount > 0 && (
          <>
            <span className="sep">·</span>
            <span className={criticalCount > 0 ? "findings-critical" : "findings-ok"}>
              {findingCount} finding{findingCount !== 1 ? "s" : ""}
              {criticalCount > 0 ? ` (${criticalCount} critical)` : ""}
            </span>
          </>
        )}
        {plan.execution_status !== "not_started" && (
          <>
            <span className="sep">·</span>
            <span>
              Exec {plan.execution_status}
              {plan.execution_exit_code != null ? ` (exit ${plan.execution_exit_code})` : ""}
            </span>
          </>
        )}
      </div>

      {disposition && <p className="plan-header-disposition">{disposition}</p>}
    </header>
  );
}
