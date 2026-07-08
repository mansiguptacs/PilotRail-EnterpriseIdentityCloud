import { useMemo, useState } from "react";
import type { Plan, PlanState } from "../types";
import { formatRelativeTime, workspaceLabel } from "../utils/format";
import Badge from "./ui/Badge";
import "./PlanQueue.css";

interface Props {
  plans: Plan[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

type Filter = "all" | "pending" | "done";

const STATE_ORDER: Record<PlanState, number> = {
  PENDING_REVIEW: 0,
  APPROVED: 1,
  AUTO_APPROVED: 2,
  REJECTED: 3,
};

function stateVariant(state: PlanState): string {
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
      return "Auto";
  }
}

function riskAccent(plan: Plan): string {
  if (plan.risk_tier === "critical") return "risk-critical";
  if (plan.risk_tier === "high") return "risk-high";
  return "";
}

export default function PlanQueue({ plans, selectedId, onSelect }: Props) {
  const [filter, setFilter] = useState<Filter>("all");

  const sorted = useMemo(() => {
    const filtered = plans.filter((p) => {
      if (filter === "pending") return p.state === "PENDING_REVIEW";
      if (filter === "done") return p.state !== "PENDING_REVIEW";
      return true;
    });
    return [...filtered].sort((a, b) => {
      const order = STATE_ORDER[a.state] - STATE_ORDER[b.state];
      if (order !== 0) return order;
      return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
    });
  }, [plans, filter]);

  const pendingCount = plans.filter((p) => p.state === "PENDING_REVIEW").length;

  return (
    <div className="plan-queue-wrap">
      <div className="plan-queue-filters">
        <button
          type="button"
          className={filter === "all" ? "active" : ""}
          onClick={() => setFilter("all")}
        >
          All ({plans.length})
        </button>
        <button
          type="button"
          className={filter === "pending" ? "active" : ""}
          onClick={() => setFilter("pending")}
        >
          Pending ({pendingCount})
        </button>
        <button
          type="button"
          className={filter === "done" ? "active" : ""}
          onClick={() => setFilter("done")}
        >
          Resolved
        </button>
      </div>

      {sorted.length === 0 ? (
        <div className="empty-state">
          {filter === "pending"
            ? "No plans awaiting review."
            : "No plans yet. Developer runs terraform apply in the gated workspace."}
        </div>
      ) : (
        <div className="plan-queue">
          {sorted.map((plan) => {
            const findings = plan.findings.length;
            const critical = plan.findings.filter((f) => f.severity === "critical").length;
            return (
              <div
                key={plan.id}
                className={`plan-item ${selectedId === plan.id ? "selected" : ""} ${riskAccent(plan)}`}
                onClick={() => onSelect(plan.id)}
              >
                <div className="plan-item-prompt">{plan.prompt}</div>
                <div className="plan-item-meta">
                  <Badge variant={stateVariant(plan.state)}>{stateLabel(plan.state)}</Badge>
                  {plan.source === "wrapper" && <Badge variant="cli">CLI</Badge>}
                  {plan.risk_tier !== "none" && (
                    <Badge variant={plan.risk_tier}>{plan.risk_tier}</Badge>
                  )}
                  {findings > 0 && (
                    <span className={`finding-pill ${critical > 0 ? "critical" : ""}`}>
                      {findings} finding{findings !== 1 ? "s" : ""}
                    </span>
                  )}
                </div>
                <div className="plan-item-sub">
                  <span>{plan.requester}</span>
                  {plan.workspace_path && (
                    <>
                      <span className="sep">·</span>
                      <span>{workspaceLabel(plan.workspace_path)}</span>
                    </>
                  )}
                  <span className="sep">·</span>
                  <span>{formatRelativeTime(plan.updated_at)}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
