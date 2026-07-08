import type { PlanState } from "../types";
import "./StateTimeline.css";

interface Props {
  currentState: PlanState;
}

export default function StateTimeline({ currentState }: Props) {
  if (currentState === "AUTO_APPROVED") {
    return (
      <div className="state-timeline">
        <h4>Plan State Machine</h4>
        <div className="timeline-steps">
          <div className="timeline-step completed">
            <div className="step-dot">&#10003;</div>
            <span className="step-label">Policy Check</span>
          </div>
          <div className="timeline-step auto-approved">
            <div className="step-dot">A</div>
            <span className="step-label">Auto-approved</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="state-timeline">
      <h4>Plan State Machine</h4>
      <div className="timeline-steps">
        <div
          className={`timeline-step ${
            currentState === "PENDING_REVIEW"
              ? "active"
              : currentState === "APPROVED" || currentState === "REJECTED"
                ? "completed"
                : ""
          }`}
        >
          <div className="step-dot">1</div>
          <span className="step-label">Pending Review</span>
        </div>
        <div
          className={`timeline-step ${
            currentState === "APPROVED"
              ? "completed"
              : currentState === "REJECTED"
                ? "rejected"
                : ""
          }`}
        >
          <div className="step-dot">{currentState === "REJECTED" ? "X" : "2"}</div>
          <span className="step-label">
            {currentState === "REJECTED" ? "Rejected" : "Approved"}
          </span>
        </div>
      </div>
    </div>
  );
}
