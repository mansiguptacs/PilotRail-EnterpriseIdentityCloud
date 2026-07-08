import { useCallback, useEffect, useRef, useState } from "react";
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
  resetDemoData,
} from "./api";
import type { AuditEntry, ConnectorHealth, DiscoveredVM, Notification, Plan, Workstation } from "./types";
import AuditLog from "./components/AuditLog";
import NotificationFeed from "./components/NotificationFeed";
import PilotRail from "./components/PilotRail";
import PlanQueue from "./components/PlanQueue";
import PromptBar from "./components/PromptBar";
import SystemStatus from "./components/SystemStatus";
import WorkstationFleet from "./components/WorkstationFleet";
import "./App.css";

type Tab = "dashboard" | "workstations" | "notifications" | "audit";

const TAB_LABELS: Record<Tab, string> = {
  dashboard: "Review queue",
  workstations: "Workstations",
  notifications: "Alerts",
  audit: "Audit log",
};

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
  const [resetLoading, setResetLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [devMenuOpen, setDevMenuOpen] = useState(false);
  const [simulateOpen, setSimulateOpen] = useState(false);
  const devMenuRef = useRef<HTMLDivElement>(null);

  const selectedPlan = plans.find((p) => p.id === selectedId) ?? null;
  const pendingCount = plans.filter((p) => p.state === "PENDING_REVIEW").length;
  const onlineAgents = workstations.filter((w) => w.agent_status === "ONLINE").length;
  const approverAlerts = notifications.filter((n) => n.event_type === "NOTIFY_APPROVER").length;

  const openPlan = useCallback((planId: string) => {
    setTab("dashboard");
    setSelectedId(planId);
  }, []);

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

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (devMenuRef.current && !devMenuRef.current.contains(e.target as Node)) {
        setDevMenuOpen(false);
      }
    }
    document.addEventListener("click", onDocClick);
    return () => document.removeEventListener("click", onDocClick);
  }, []);

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

  async function handleResetDemo() {
    if (
      !window.confirm(
        "Clear all plans, approvals, rejections, audit log, and notifications? Workstation fleet is kept."
      )
    ) {
      return;
    }
    setResetLoading(true);
    setDevMenuOpen(false);
    setError(null);
    try {
      await resetDemoData({ reviewer_initials: "SEC" });
      setSelectedId(null);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reset demo data");
    } finally {
      setResetLoading(false);
    }
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <span className="brand-title">Pilot Rail</span>
          <span className="product-module">AI Onboarding · Apply Gate</span>
        </div>

        <nav className="sidebar-nav">
          <button
            className={`nav-item ${tab === "dashboard" ? "active" : ""}`}
            onClick={() => setTab("dashboard")}
          >
            <span>Review queue</span>
            {pendingCount > 0 && <span className="nav-badge">{pendingCount}</span>}
          </button>
          <button
            className={`nav-item ${tab === "workstations" ? "active" : ""}`}
            onClick={() => setTab("workstations")}
          >
            <span>Workstations</span>
            {onlineAgents > 0 && <span className="nav-badge muted">{onlineAgents}</span>}
          </button>
          <button
            className={`nav-item ${tab === "notifications" ? "active" : ""}`}
            onClick={() => setTab("notifications")}
          >
            <span>Alerts</span>
            {approverAlerts > 0 && <span className="nav-badge">{approverAlerts}</span>}
          </button>
          <button
            className={`nav-item ${tab === "audit" ? "active" : ""}`}
            onClick={() => setTab("audit")}
          >
            <span>Audit log</span>
          </button>
        </nav>

        <div className="sidebar-footer">
          <span className="sidebar-footer-label">Terraform apply gate</span>
        </div>
      </aside>

      <div className="app-main">
        <header className="topbar">
          <div className="topbar-left">
            <span className="breadcrumb-muted">Identity Security</span>
            <span className="breadcrumb-sep">/</span>
            <span className="breadcrumb-current">{TAB_LABELS[tab]}</span>
          </div>
          <div className="topbar-right">
            {pendingCount > 0 && tab === "dashboard" && (
              <span className="topbar-pill">{pendingCount} pending review</span>
            )}
            <button type="button" className="topbar-btn" onClick={refresh} title="Refresh">
              Refresh
            </button>
            <div className="dev-menu-wrap" ref={devMenuRef}>
              <button
                type="button"
                className="topbar-btn"
                onClick={() => setDevMenuOpen((v) => !v)}
              >
                Tools
              </button>
              {devMenuOpen && (
                <div className="dev-menu">
                  <button type="button" onClick={() => setSimulateOpen((v) => !v)}>
                    {simulateOpen ? "Hide" : "Show"} simulate request
                  </button>
                  <button type="button" onClick={handleResetDemo} disabled={resetLoading}>
                    {resetLoading ? "Resetting…" : "Reset demo data"}
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        <SystemStatus connectors={connectors} />

        {error && <div className="error-banner">{error}</div>}

        <div className="main-content">
          {tab === "dashboard" ? (
            <div className="dashboard">
              <div className="left-panel card">
                {simulateOpen && (
                  <div className="simulate-panel">
                    <PromptBar onSubmit={handleCreatePlan} loading={loading} />
                  </div>
                )}
                <div className="panel-header">Apply requests</div>
                <PlanQueue plans={plans} selectedId={selectedId} onSelect={setSelectedId} />
              </div>
              <div className="right-panel card">
                {selectedPlan ? (
                  <PilotRail
                    plan={selectedPlan}
                    onApprove={handleApprove}
                    onReject={handleReject}
                    actionLoading={actionLoading}
                  />
                ) : (
                  <div className="empty-state empty-state-detail">
                    <div className="empty-icon" />
                    <h2>Select a request to review</h2>
                    <p>
                      When a developer runs <code>terraform apply</code> in a gated workspace,
                      blocked requests appear here for security approval.
                    </p>
                  </div>
                )}
              </div>
            </div>
          ) : tab === "workstations" ? (
            <div className="page-card">
              <WorkstationFleet
                workstations={workstations}
                discovered={discovered}
                onRefresh={refresh}
              />
            </div>
          ) : tab === "notifications" ? (
            <div className="page-card">
              <NotificationFeed notifications={notifications} onOpenPlan={openPlan} />
            </div>
          ) : (
            <div className="page-card">
              <AuditLog entries={auditEntries} onOpenPlan={openPlan} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
