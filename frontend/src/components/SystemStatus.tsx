import { useState } from "react";
import type { ConnectorHealth } from "../types";
import { formatRelativeTime } from "../utils/format";
import "./SystemStatus.css";

interface Props {
  connectors: ConnectorHealth[];
}

export default function SystemStatus({ connectors }: Props) {
  const [expanded, setExpanded] = useState(false);

  const degraded = connectors.filter((c) => c.status !== "healthy");
  const summary =
    degraded.length === 0
      ? "All systems operational"
      : `${degraded.length} issue${degraded.length > 1 ? "s" : ""}: ${degraded.map((c) => c.name).join(", ")}`;

  const worstStatus = connectors.some((c) => c.status === "down")
    ? "down"
    : degraded.length > 0
      ? "degraded"
      : "healthy";

  return (
    <div className="system-status">
      <button
        type="button"
        className="system-status-toggle"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
      >
        <span className={`system-status-dot ${worstStatus}`} />
        <span className="system-status-summary">{summary}</span>
        <span className="system-status-chevron">{expanded ? "▾" : "▸"}</span>
      </button>

      {expanded && (
        <table className="system-status-table">
          <thead>
            <tr>
              <th>Connector</th>
              <th>Status</th>
              <th>Detail</th>
              <th>Checked</th>
            </tr>
          </thead>
          <tbody>
            {connectors.map((c) => (
              <tr key={c.name}>
                <td>{c.name}</td>
                <td>
                  <span className={`system-status-dot ${c.status}`} />
                  {c.status}
                </td>
                <td className="detail-cell">{c.message}</td>
                <td className="time-cell">{formatRelativeTime(c.last_checked)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
