import { useState } from "react";
import { pushWorkstation, revokeWorkstation } from "../api";
import type { AgentStatus, DiscoveredVM, Workstation } from "../types";
import "./WorkstationFleet.css";

interface Props {
  workstations: Workstation[];
  discovered: DiscoveredVM[];
  onRefresh: () => Promise<void>;
}

function statusClass(status: AgentStatus | string): string {
  return status.toLowerCase().replace("_", "_");
}

function formatLastSeen(ts: string | null): string {
  if (!ts) return "never";
  const diff = Date.now() - new Date(ts).getTime();
  const secs = Math.floor(diff / 1000);
  if (secs < 60) return `${secs}s ago`;
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m ago`;
  return `${Math.floor(mins / 60)}h ago`;
}

export default function WorkstationFleet({
  workstations,
  discovered,
  onRefresh,
}: Props) {
  const [initials, setInitials] = useState("SEC");
  const [manualEndpoint, setManualEndpoint] = useState("");
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const onlineCount = workstations.filter((w) => w.agent_status === "ONLINE").length;
  const deployedCount = workstations.filter((w) => w.state === "DEPLOYED").length;

  function parseEndpoint(raw: string): { ip: string; ssh_port: number } {
    const trimmed = raw.trim();
    if (!trimmed) return { ip: "", ssh_port: 2222 };
    if (trimmed.includes(":")) {
      const [ip, port] = trimmed.split(":");
      return { ip, ssh_port: parseInt(port, 10) || 2222 };
    }
    return { ip: trimmed, ssh_port: 2222 };
  }

  async function handleDeploy(target: {
    ip?: string;
    vm_name?: string;
    ssh_port?: number;
  }) {
    if (!initials.trim()) {
      setError("Reviewer initials required");
      return;
    }
    const key = target.vm_name || target.ip || "manual";
    setLoading(key);
    setError(null);
    try {
      await pushWorkstation({
        ...target,
        reviewer_initials: initials.trim(),
        ssh_user: "developer",
      });
      await onRefresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Deploy failed");
    } finally {
      setLoading(null);
    }
  }

  async function handleRevoke(id: string) {
    if (!initials.trim()) return;
    setLoading(id);
    setError(null);
    try {
      await revokeWorkstation(id, initials.trim());
      await onRefresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Revoke failed");
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="workstation-fleet">
      <div className="fleet-summary">
        <span>
          Discovered: <strong>{discovered.length}</strong>
        </span>
        <span>
          Deployed: <strong>{deployedCount}</strong>
        </span>
        <span>
          Agents online: <strong>{onlineCount}</strong>
        </span>
      </div>

      <div className="fleet-section">
        <h3>IT Admin — Deploy Apply Gate</h3>
        <div className="deploy-form">
          <input
            placeholder="Reviewer initials (e.g. SEC)"
            value={initials}
            onChange={(e) => setInitials(e.target.value)}
          />
          <input
            placeholder="Manual endpoint e.g. 127.0.0.1:2222 (optional)"
            value={manualEndpoint}
            onChange={(e) => setManualEndpoint(e.target.value)}
          />
          <button
            className="btn-deploy"
            disabled={!!loading || !manualEndpoint.trim()}
            onClick={() => {
              const { ip, ssh_port } = parseEndpoint(manualEndpoint);
              handleDeploy({ ip, ssh_port });
            }}
          >
            Deploy to Endpoint
          </button>
        </div>
        {error && <div className="fleet-error">{error}</div>}
      </div>

      <div className="fleet-section">
        <h3>Discovered Workstations (Docker)</h3>
        {discovered.length === 0 ? (
          <div className="empty-state">
            No containers found. Run: bash scripts/provision-dev-container.sh
          </div>
        ) : (
          <table className="fleet-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Endpoint</th>
                <th>Discovery</th>
                <th>Agent</th>
                <th>Deploy State</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {discovered.map((ws) => (
                <tr key={`${ws.vm_name}-${ws.endpoint}`}>
                  <td>{ws.vm_name || "—"}</td>
                  <td>{ws.endpoint || `${ws.ip}:${ws.ssh_port}`}</td>
                  <td>
                    <span className="status-badge">{ws.discovery_source}</span>
                  </td>
                  <td>
                    <span className={`status-badge ${statusClass(ws.agent_status)}`}>
                      {ws.agent_status}
                    </span>
                  </td>
                  <td>
                    <span className={`status-badge ${statusClass(ws.deploy_state)}`}>
                      {ws.deploy_state}
                    </span>
                  </td>
                  <td>
                    {ws.deploy_state !== "DEPLOYED" && ws.deploy_state !== "DEPLOYING" ? (
                      <button
                        className="btn-deploy"
                        disabled={!!loading}
                        onClick={() =>
                          handleDeploy({
                            ip: ws.ip,
                            vm_name: ws.vm_name,
                            ssh_port: ws.ssh_port,
                          })
                        }
                      >
                        {loading === (ws.vm_name || ws.ip) ? "Deploying…" : "Deploy Gate"}
                      </button>
                    ) : (
                      <span style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>
                        {ws.deploy_state === "DEPLOYING" ? "Deploying…" : "Deployed"}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="fleet-section">
        <h3>Fleet — Managed Workstations</h3>
        {workstations.length === 0 ? (
          <div className="empty-state">No workstations in fleet yet.</div>
        ) : (
          <table className="fleet-table">
            <thead>
              <tr>
                <th>Host</th>
                <th>Endpoint</th>
                <th>Agent</th>
                <th>Gate</th>
                <th>Last Seen</th>
                <th>Deployed By</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {workstations.map((ws) => (
                <tr key={ws.id}>
                  <td>{ws.hostname || ws.vm_name || "—"}</td>
                  <td>
                    {ws.ip}
                    {ws.ssh_port ? `:${ws.ssh_port}` : ""}
                  </td>
                  <td>
                    <span className={`status-badge ${statusClass(ws.agent_status)}`}>
                      {ws.agent_status}
                    </span>
                  </td>
                  <td>{ws.gate_active ? "Yes" : "No"}</td>
                  <td>{formatLastSeen(ws.last_seen_at)}</td>
                  <td>{ws.deployed_by || "—"}</td>
                  <td>
                    {ws.state === "DEPLOYED" && (
                      <button
                        className="btn-revoke"
                        disabled={!!loading}
                        onClick={() => handleRevoke(ws.id)}
                      >
                        Revoke
                      </button>
                    )}
                    {ws.last_error && (
                      <div className="fleet-error" title={ws.last_error}>
                        failed
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
