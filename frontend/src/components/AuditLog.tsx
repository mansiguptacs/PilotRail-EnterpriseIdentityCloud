import type { AuditEntry } from "../types";
import { shortId } from "../utils/format";
import "./AuditLog.css";

interface Props {
  entries: AuditEntry[];
  onOpenPlan: (planId: string) => void;
}

function actionClass(action: string): string {
  if (action === "APPROVE" || action === "AUTO_APPROVE") return "action-approve";
  if (action === "REJECT") return "action-reject";
  if (action.startsWith("NOTIFY")) return "action-notify";
  if (action === "EXECUTE") return "action-execute";
  if (action.startsWith("AGENT")) return "action-agent";
  return "action-neutral";
}

export default function AuditLog({ entries, onOpenPlan }: Props) {
  if (entries.length === 0) {
    return <div className="empty-state">No audit entries yet.</div>;
  }

  return (
    <div className="audit-log">
      <table className="audit-table">
        <thead>
          <tr>
            <th>Time</th>
            <th>Action</th>
            <th>Reviewer</th>
            <th>Plan</th>
            <th>Transition</th>
            <th>Comment</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry) => (
            <tr key={entry.id}>
              <td>{new Date(entry.timestamp).toLocaleString()}</td>
              <td className={actionClass(entry.action)}>{entry.action}</td>
              <td>{entry.reviewer_initials}</td>
              <td>
                <button
                  type="button"
                  className="plan-link"
                  onClick={() => onOpenPlan(entry.plan_id)}
                  title={entry.plan_id}
                >
                  {shortId(entry.plan_id)}…
                </button>
              </td>
              <td>
                {entry.previous_state} → {entry.new_state}
              </td>
              <td>{entry.comment || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
