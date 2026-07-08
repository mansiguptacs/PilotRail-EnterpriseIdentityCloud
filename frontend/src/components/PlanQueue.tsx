import type { Plan, PlanState } from "../types";
import "./PlanQueue.css";

interface Props {
  plans: Plan[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

function stateClass(state: PlanState): string {
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

function stateLabel(state: PlanState): string {
  switch (state) {
    case "PENDING_REVIEW":
      return "Pending";
    case "APPROVED":
      return "Approved";
    case "REJECTED":
      return "Rejected";
    case "AUTO_APPROVED":
      return "Auto-approved";
  }
}

export default function PlanQueue({ plans, selectedId, onSelect }: Props) {
  if (plans.length === 0) {
    return (
      <div className="empty-state">
        No plans yet. Run <code>terraform apply</code> in the demo workspace.
      </div>
    );
  }

  return (
    <div className="plan-queue">
      {plans.map((plan) => (
        <div
          key={plan.id}
          className={`plan-item ${selectedId === plan.id ? "selected" : ""}`}
          onClick={() => onSelect(plan.id)}
        >
          <div className="plan-item-prompt">{plan.prompt}</div>
          <div className="plan-item-meta">
            <span className={`state-badge ${stateClass(plan.state)}`}>
              {stateLabel(plan.state)}
            </span>
            {plan.source === "wrapper" && (
              <span className="source-badge">CLI</span>
            )}
            {plan.risk_tier !== "none" && (
              <span className={`risk-badge ${plan.risk_tier}`}>{plan.risk_tier}</span>
            )}
            {plan.security_warning && <span className="warning-dot" title="Security warning" />}
            <span>{plan.requester}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
