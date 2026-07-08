import type { AuditEntry } from "../types";
import "./AuditLog.css";

interface Props {
  entries: AuditEntry[];
}

export default function AuditLog({ entries }: Props) {
  if (entries.length === 0) {
    return <div className="empty-state">No audit entries yet.</div>;
  }

  return (
    <div className="audit-log">
      <table className="audit-table">
        <thead>
          <tr>
            <th>Timestamp</th>
            <th>Action</th>
            <th>Reviewer</th>
            <th>Plan ID</th>
            <th>Transition</th>
            <th>Comment</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry) => (
            <tr key={entry.id}>
              <td>{new Date(entry.timestamp).toLocaleString()}</td>
              <td className={entry.action === "APPROVE" ? "action-approve" : "action-reject"}>
                {entry.action}
              </td>
              <td>{entry.reviewer_initials}</td>
              <td className="plan-id-cell">{entry.plan_id.slice(0, 8)}...</td>
              <td>
                {entry.previous_state} &rarr; {entry.new_state}
              </td>
              <td>{entry.comment || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
