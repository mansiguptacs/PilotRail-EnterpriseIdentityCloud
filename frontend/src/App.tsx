import { useCallback, useEffect, useState } from "react";
import {
  approvePlan,
  createPlan,
  discoverWorkstations,
  fetchAuditLog,
  fetchConnectorHealth,
  fetchNotifications,
  fetchPlans,
  fetchWorkstations,
  rejectPlan,
} from "./api";
import type { AuditEntry, ConnectorHealth, DiscoveredVM, Notification, Plan, Workstation } from "./types";
import AuditLog from "./components/AuditLog";
import ConnectorHealthStrip from "./components/ConnectorHealthStrip";
import NotificationFeed from "./components/NotificationFeed";
import PilotRail from "./components/PilotRail";
import PlanQueue from "./components/PlanQueue";
import PromptBar from "./components/PromptBar";
import WorkstationFleet from "./components/WorkstationFleet";
import "./App.css";

type Tab = "dashboard" | "workstations" | "notifications" | "audit";

export default function App() {
  const [tab, setTab] = useState<Tab>("dashboard");
  const [plans, setPlans] = useState<Plan[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [auditEntries, setAuditEntries] = useState<AuditEntry[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [connectors, setConnectors] = useState<ConnectorHealth[]>([]);
  const [workstations, setWorkstations] = useState<Workstation[]>([]);
  const [discovered, setDiscovered] = useState<DiscoveredVM[]>([]);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedPlan = plans.find((p) => p.id === selectedId) ?? null;
  const pendingCount = plans.filter((p) => p.state === "PENDING_REVIEW").length;
  const onlineAgents = workstations.filter((w) => w.agent_status === "ONLINE").length;

  const refresh = useCallback(async () => {
    try {
      const [plansData, auditData, connectorData, notificationData, wsData, discData] =
        await Promise.all([
          fetchPlans(),
          fetchAuditLog(),
          fetchConnectorHealth(),
          fetchNotifications(),
          fetchWorkstations(),
          discoverWorkstations(),
        ]);
      setPlans(plansData);
      setAuditEntries(auditData);
      setConnectors(connectorData);
      setNotifications(notificationData);
      setWorkstations(wsData);
      setDiscovered(discData);
      if (selectedId && !plansData.find((p) => p.id === selectedId)) {
        setSelectedId(plansData[0]?.id ?? null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch data");
    }
  }, [selectedId]);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 5000);
    return () => clearInterval(interval);
  }, [refresh]);

  async function handleCreatePlan(prompt: string) {
    setLoading(true);
    setError(null);
    try {
      const plan = await createPlan(prompt);
      await refresh();
      setSelectedId(plan.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create plan");
    } finally {
      setLoading(false);
    }
  }

  async function handleApprove(initials: string) {
    if (!selectedId) return;
    setActionLoading(true);
    setError(null);
    try {
      await approvePlan(selectedId, initials);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to approve plan");
    } finally {
      setActionLoading(false);
    }
  }

  async function handleReject(initials: string, comment: string) {
    if (!selectedId) return;
    setActionLoading(true);
    setError(null);
    try {
      await rejectPlan(selectedId, initials, comment);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reject plan");
    } finally {
      setActionLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="header">
        <h1>Pilot Rail Mini</h1>
        <p>Transparent apply gate for AI-generated infrastructure and access changes</p>
      </header>

      <ConnectorHealthStrip connectors={connectors} />

      <div className="tabs">
        <button
          className={`tab ${tab === "dashboard" ? "active" : ""}`}
          onClick={() => setTab("dashboard")}
        >
          Pilot Rail Dashboard
          {pendingCount > 0 && <span className="tab-badge">{pendingCount}</span>}
        </button>
        <button
          className={`tab ${tab === "workstations" ? "active" : ""}`}
          onClick={() => setTab("workstations")}
        >
          Workstations
          {onlineAgents > 0 && <span className="tab-badge">{onlineAgents}</span>}
        </button>
        <button
          className={`tab ${tab === "notifications" ? "active" : ""}`}
          onClick={() => setTab("notifications")}
        >
          Notifications
          {notifications.length > 0 && (
            <span className="tab-badge">{notifications.length}</span>
          )}
        </button>
        <button
          className={`tab ${tab === "audit" ? "active" : ""}`}
          onClick={() => setTab("audit")}
        >
          Audit Log
        </button>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="refresh-bar">
        <button className="refresh-btn" onClick={refresh}>
          Refresh
        </button>
      </div>

      <div className="main-content">
        {tab === "dashboard" ? (
          <div className="dashboard">
            <div className="left-panel">
              <PromptBar onSubmit={handleCreatePlan} loading={loading} />
              <div className="panel-header">Plan Queue</div>
              <PlanQueue
                plans={plans}
                selectedId={selectedId}
                onSelect={setSelectedId}
              />
            </div>
            <div className="right-panel">
              <div className="panel-header">Pilot Rail Interface</div>
              {selectedPlan ? (
                <PilotRail
                  plan={selectedPlan}
                  onApprove={handleApprove}
                  onReject={handleReject}
                  actionLoading={actionLoading}
                />
              ) : (
                <div className="empty-state">
                  Select a plan from the queue. Dev runs terraform apply in the VM.
                </div>
              )}
            </div>
          </div>
        ) : tab === "workstations" ? (
          <WorkstationFleet
            workstations={workstations}
            discovered={discovered}
            onRefresh={refresh}
          />
        ) : tab === "notifications" ? (
          <NotificationFeed notifications={notifications} />
        ) : (
          <AuditLog entries={auditEntries} />
        )}
      </div>
    </div>
  );
}
