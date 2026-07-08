import { useState } from "react";
import type { Plan } from "../types";
import PilotAgentPanel from "./PilotAgentPanel";
import SecurityAlert from "./SecurityAlert";
import StateTimeline from "./StateTimeline";
import "./PilotRail.css";

interface Props {
  plan: Plan;
  onApprove: (initials: string) => Promise<void>;
  onReject: (initials: string, comment: string) => Promise<void>;
  actionLoading: boolean;
}

export default function PilotRail({ plan, onApprove, onReject, actionLoading }: Props) {
  const [initials, setInitials] = useState("");
  const [rejectComment, setRejectComment] = useState("");

  const isPending = plan.state === "PENDING_REVIEW";
  const canApprove = isPending && initials.trim().length > 0 && !actionLoading;
  const canReject =
    isPending && initials.trim().length > 0 && rejectComment.trim().length > 0 && !actionLoading;

  const sodConflict =
    isPending &&
    initials.trim().length > 0 &&
    initials.trim().toLowerCase() === plan.requester.toLowerCase();

  return (
    <div className="pilot-rail">
      <StateTimeline currentState={plan.state} />

      <div className={`enforcement-banner ${plan.enforcement_level}`}>
        <span className="enforcement-label">{plan.enforcement_level.replace("_", " ")}</span>
        <span>Risk: {plan.risk_tier}</span>
        <span>Requester: {plan.requester}</span>
        <span>Source: {plan.source}</span>
      </div>

      <PilotAgentPanel plan={plan} />

      {plan.security_warning && <SecurityAlert findings={plan.findings} />}

      <div className="rail-section">
        <h3>Request</h3>
        <p className="prompt-text">{plan.prompt}</p>
      </div>

      {plan.reasoning && (
        <div className="rail-section">
          <h3>Context</h3>
          <p className="reasoning">{plan.reasoning}</p>
        </div>
      )}

      <div className="meta-row">
        <span>Generator: {plan.model}</span>
        <span>Scanner: {plan.scan_model}</span>
        <span>Hash: {plan.context_packet_hash.slice(0, 12)}...</span>
      </div>

      <pre className={`code-block ${plan.state === "REJECTED" ? "rejected" : ""}`}>
        {plan.code}
      </pre>

      {plan.state === "AUTO_APPROVED" && (
        <div className="disposition-banner auto-approved">
          Auto-approved by policy engine
        </div>
      )}

      {plan.state === "APPROVED" && (
        <div className="disposition-banner approved">
          Approved by {plan.reviewer_initials}
        </div>
      )}

      {plan.state === "REJECTED" && (
        <div className="disposition-banner rejected">
          Rejected by {plan.reviewer_initials}: {plan.reject_comment}
        </div>
      )}

      {plan.execution_status !== "not_started" && plan.execution_output && (
        <div className="execution-panel">
          <h3>Terraform Execution ({plan.execution_status})</h3>
          <pre className="execution-output">{plan.execution_output}</pre>
        </div>
      )}

      {isPending && (
        <div className="approval-controls">
          <h3>Human Review Gate</h3>
          <p className="sod-note">
            Approver must differ from requester ({plan.requester}) — separation of duties.
          </p>
          <div className="initials-field">
            <label htmlFor="initials">Reviewer Initials</label>
            <input
              id="initials"
              type="text"
              value={initials}
              onChange={(e) => setInitials(e.target.value)}
              placeholder="e.g. SEC (not the requester)"
              maxLength={10}
            />
            {sodConflict && (
              <p className="sod-error">Cannot approve: same person as requester</p>
            )}
          </div>
          <div className="reject-field">
            <label htmlFor="reject-comment">Rejection Comment (required to reject)</label>
            <textarea
              id="reject-comment"
              value={rejectComment}
              onChange={(e) => setRejectComment(e.target.value)}
              placeholder="Explain why this plan should not proceed..."
            />
          </div>
          <div className="action-buttons">
            <button
              className="btn-approve"
              disabled={!canApprove || sodConflict}
              onClick={() => onApprove(initials.trim())}
            >
              Approve Plan
            </button>
            <button
              className="btn-reject"
              disabled={!canReject || sodConflict}
              onClick={() => onReject(initials.trim(), rejectComment.trim())}
            >
              Reject Plan
            </button>
          </div>
          <p className="sod-note" style={{ marginTop: "0.75rem" }}>
            On approve/reject, the requester is notified to re-run terraform apply.
          </p>
        </div>
      )}
    </div>
  );
}
