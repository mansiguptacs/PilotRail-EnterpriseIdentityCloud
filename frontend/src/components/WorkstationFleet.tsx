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
  const [manualIp, setManualIp] = useState("");
  const [manualVm, setManualVm] = useState("");
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const onlineCount = workstations.filter((w) => w.agent_status === "ONLINE").length;
  const deployedCount = workstations.filter((w) => w.state === "DEPLOYED").length;

  async function handleDeploy(target: { ip?: string; vm_name?: string }) {
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
        ssh_user: "ubuntu",
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
            placeholder="Manual IP (optional)"
            value={manualIp}
            onChange={(e) => setManualIp(e.target.value)}
          />
          <input
            placeholder="VM name (optional)"
            value={manualVm}
            onChange={(e) => setManualVm(e.target.value)}
          />
          <button
            className="btn-deploy"
            disabled={!!loading || (!manualIp && !manualVm)}
            onClick={() =>
              handleDeploy({
                ip: manualIp || undefined,
                vm_name: manualVm || undefined,
              })
            }
          >
            Deploy to IP
          </button>
        </div>
        {error && <div className="fleet-error">{error}</div>}
      </div>

      <div className="fleet-section">
        <h3>Discovered VMs (Multipass)</h3>
        {discovered.length === 0 ? (
          <div className="empty-state">
            No running VMs found. Run: bash scripts/provision-dev-vm.sh
          </div>
        ) : (
          <table className="fleet-table">
            <thead>
              <tr>
                <th>VM Name</th>
                <th>IP</th>
                <th>Agent</th>
                <th>Deploy State</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {discovered.map((vm) => (
                <tr key={`${vm.vm_name}-${vm.ip}`}>
                  <td>{vm.vm_name || "—"}</td>
                  <td>{vm.ip}</td>
                  <td>
                    <span className={`status-badge ${statusClass(vm.agent_status)}`}>
                      {vm.agent_status}
                    </span>
                  </td>
                  <td>
                    <span className={`status-badge ${statusClass(vm.deploy_state)}`}>
                      {vm.deploy_state}
                    </span>
                  </td>
                  <td>
                    {vm.deploy_state !== "DEPLOYED" && vm.deploy_state !== "DEPLOYING" ? (
                      <button
                        className="btn-deploy"
                        disabled={!!loading}
                        onClick={() =>
                          handleDeploy({ ip: vm.ip, vm_name: vm.vm_name })
                        }
                      >
                        {loading === (vm.vm_name || vm.ip) ? "Deploying…" : "Deploy Gate"}
                      </button>
                    ) : (
                      <span style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>
                        {vm.deploy_state === "DEPLOYING" ? "Deploying…" : "Deployed"}
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
                <th>IP</th>
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
                  <td>{ws.ip}</td>
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
