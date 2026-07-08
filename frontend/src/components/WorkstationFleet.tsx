import { useMemo, useState } from "react";
import { pushWorkstation, revokeWorkstation } from "../api";
import type { DiscoveredVM, Workstation } from "../types";
import Badge from "./ui/Badge";
import "./WorkstationFleet.css";

interface Props {
  workstations: Workstation[];
  discovered: DiscoveredVM[];
  onRefresh: () => Promise<void>;
}

type FleetRow = {
  key: string;
  name: string;
  endpoint: string;
  registration: string;
  agentStatus: string;
  deployState: string;
  gate: string;
  shim: string;
  lastSeen: string;
  deployedBy: string;
  workstationId: string | null;
  lastError: string | null;
  deployTarget: { ip?: string; vm_name?: string; ssh_port?: number } | null;
};

function statusVariant(status: string): string {
  const s = status.toLowerCase();
  if (s === "online" || s === "deployed" || s === "healthy") return "approved";
  if (s === "offline" || s === "failed" || s === "revoked") return "rejected";
  if (s === "stale" || s === "pending_push" || s === "deploying") return "pending";
  return "neutral";
}

function formatLastSeen(ts: string | null): string {
  if (!ts) return "—";
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

  const rows = useMemo(() => {
    const managedKeys = new Set(
      workstations.map((w) => `${w.vm_name || w.hostname}:${w.ip}:${w.ssh_port ?? 22}`)
    );
    const result: FleetRow[] = [];

    for (const ws of workstations) {
      result.push({
        key: ws.id,
        name: ws.hostname || ws.vm_name || "—",
        endpoint: `${ws.ip}${ws.ssh_port ? `:${ws.ssh_port}` : ""}`,
        registration: "Managed",
        agentStatus: ws.agent_status,
        deployState: ws.state,
        gate: ws.gate_active ? "Active" : "Off",
        shim: ws.shim_version || "—",
        lastSeen: formatLastSeen(ws.last_seen_at),
        deployedBy: ws.deployed_by || "—",
        workstationId: ws.id,
        lastError: ws.last_error,
        deployTarget: null,
      });
    }

    for (const d of discovered) {
      if ([...managedKeys].some((k) => k.includes(d.ip) && k.includes(String(d.vm_name)))) {
        continue;
      }
      if (d.workstation_id && workstations.some((w) => w.id === d.workstation_id)) {
        continue;
      }
      result.push({
        key: `disc-${d.vm_name}-${d.endpoint}`,
        name: d.vm_name || "—",
        endpoint: d.endpoint || `${d.ip}:${d.ssh_port}`,
        registration: d.discovery_source,
        agentStatus: d.agent_status,
        deployState: d.deploy_state,
        gate: d.deploy_state === "DEPLOYED" ? "Active" : "—",
        shim: "—",
        lastSeen: "—",
        deployedBy: "—",
        workstationId: d.workstation_id,
        lastError: null,
        deployTarget: { ip: d.ip, vm_name: d.vm_name, ssh_port: d.ssh_port },
      });
    }

    return result;
  }, [workstations, discovered]);

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
      <div className="fleet-kpis">
        <div className="kpi">
          <span className="kpi-value">{discovered.length}</span>
          <span className="kpi-label">Discovered</span>
        </div>
        <div className="kpi">
          <span className="kpi-value">{deployedCount}</span>
          <span className="kpi-label">Gate deployed</span>
        </div>
        <div className="kpi">
          <span className="kpi-value">{onlineCount}</span>
          <span className="kpi-label">Agents online</span>
        </div>
      </div>

      <div className="fleet-section">
        <h3>IT admin — push apply gate</h3>
        <div className="deploy-form">
          <input
            placeholder="Reviewer initials (e.g. SEC)"
            value={initials}
            onChange={(e) => setInitials(e.target.value)}
          />
          <input
            placeholder="Manual endpoint e.g. pilot-dev:22 (optional)"
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
            Deploy to endpoint
          </button>
        </div>
        {error && <div className="fleet-error">{error}</div>}
      </div>

      <div className="fleet-section">
        <h3>Workstation fleet</h3>
        {rows.length === 0 ? (
          <div className="empty-state">No workstations discovered. Start the demo stack.</div>
        ) : (
          <table className="fleet-table">
            <thead>
              <tr>
                <th>Host</th>
                <th>Endpoint</th>
                <th>Source</th>
                <th>Agent</th>
                <th>Deploy</th>
                <th>Gate</th>
                <th>Shim</th>
                <th>Last seen</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.key}>
                  <td>{row.name}</td>
                  <td className="mono">{row.endpoint}</td>
                  <td>
                    <Badge variant="neutral">{row.registration}</Badge>
                  </td>
                  <td>
                    <Badge variant={statusVariant(row.agentStatus)}>{row.agentStatus}</Badge>
                  </td>
                  <td>
                    <Badge variant={statusVariant(row.deployState)}>{row.deployState}</Badge>
                  </td>
                  <td>{row.gate}</td>
                  <td className="mono">{row.shim}</td>
                  <td>{row.lastSeen}</td>
                  <td className="action-cell">
                    {row.deployTarget &&
                      row.deployState !== "DEPLOYED" &&
                      row.deployState !== "DEPLOYING" && (
                        <button
                          className="btn-deploy"
                          disabled={!!loading}
                          onClick={() => handleDeploy(row.deployTarget!)}
                        >
                          {loading === (row.deployTarget.vm_name || row.deployTarget.ip)
                            ? "Deploying…"
                            : "Deploy"}
                        </button>
                      )}
                    {row.workstationId && row.deployState === "DEPLOYED" && (
                      <button
                        className="btn-revoke"
                        disabled={!!loading}
                        onClick={() => handleRevoke(row.workstationId!)}
                      >
                        Revoke
                      </button>
                    )}
                    {row.lastError && (
                      <span className="fleet-error-inline" title={row.lastError}>
                        error
                      </span>
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
