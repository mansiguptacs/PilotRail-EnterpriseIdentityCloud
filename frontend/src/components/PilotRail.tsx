import { useState } from "react";
import type { Plan } from "../types";
import PilotAgentPanel from "./PilotAgentPanel";
import PlanHeader from "./PlanHeader";
import SecurityAlert from "./SecurityAlert";
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
      <PlanHeader plan={plan} />

      {plan.findings.length > 0 && <SecurityAlert findings={plan.findings} />}

      {(isPending || plan.pilot_guidance.message) && <PilotAgentPanel plan={plan} />}

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
        <span title={plan.context_packet_hash}>Hash: {plan.context_packet_hash.slice(0, 12)}…</span>
      </div>

      <pre className={`code-block ${plan.state === "REJECTED" ? "rejected" : ""}`}>
        {plan.code}
      </pre>

      {plan.execution_status !== "not_started" && (
        <div className="execution-panel">
          <h3>
            Terraform execution — {plan.execution_status}
            {plan.execution_exit_code != null && ` (exit ${plan.execution_exit_code})`}
          </h3>
          {plan.execution_output ? (
            <pre className="execution-output">{plan.execution_output}</pre>
          ) : (
            <p className="execution-empty">No output captured.</p>
          )}
        </div>
      )}

      {isPending && (
        <div className="approval-controls approval-sticky">
          <h3>Human review gate</h3>
          <p className="sod-note">
            Approver must differ from requester ({plan.requester}) — separation of duties.
          </p>
          <div className="initials-field">
            <label htmlFor="initials">Reviewer initials</label>
            <input
              id="initials"
              type="text"
              value={initials}
              onChange={(e) => setInitials(e.target.value)}
              placeholder="e.g. SEC"
              maxLength={10}
            />
            {sodConflict && (
              <p className="sod-error">Cannot approve: same person as requester</p>
            )}
          </div>
          <div className="reject-field">
            <label htmlFor="reject-comment">Rejection comment (required to reject)</label>
            <textarea
              id="reject-comment"
              value={rejectComment}
              onChange={(e) => setRejectComment(e.target.value)}
              placeholder="Explain why this plan should not proceed…"
            />
          </div>
          <div className="action-buttons">
            <button
              className="btn-approve"
              disabled={!canApprove || sodConflict}
              onClick={() => onApprove(initials.trim())}
            >
              Approve plan
            </button>
            <button
              className="btn-reject"
              disabled={!canReject || sodConflict}
              onClick={() => onReject(initials.trim(), rejectComment.trim())}
            >
              Reject plan
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
