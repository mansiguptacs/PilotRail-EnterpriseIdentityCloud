import type {
  AuditEntry,
  ConnectorHealth,
  DiscoveredVM,
  Notification,
  Plan,
  Workstation,
} from "./types";

const API_BASE = "http://localhost:8000/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || "Request failed");
  }
  return response.json();
}

export function fetchPlans(): Promise<Plan[]> {
  return request<Plan[]>("/plans");
}

export function fetchPlan(id: string): Promise<Plan> {
  return request<Plan>(`/plans/${id}`);
}

export function createPlan(prompt: string): Promise<Plan> {
  return request<Plan>("/plans", {
    method: "POST",
    body: JSON.stringify({ prompt }),
  });
}

export function approvePlan(id: string, reviewer_initials: string): Promise<Plan> {
  return request<Plan>(`/plans/${id}/approve`, {
    method: "POST",
    body: JSON.stringify({ reviewer_initials }),
  });
}

export function rejectPlan(
  id: string,
  reviewer_initials: string,
  comment: string
): Promise<Plan> {
  return request<Plan>(`/plans/${id}/reject`, {
    method: "POST",
    body: JSON.stringify({ reviewer_initials, comment }),
  });
}

export function fetchAuditLog(): Promise<AuditEntry[]> {
  return request<AuditEntry[]>("/audit");
}

export function fetchConnectorHealth(): Promise<ConnectorHealth[]> {
  return request<ConnectorHealth[]>("/connectors/health");
}

export function fetchNotifications(): Promise<Notification[]> {
  return request<Notification[]>("/notifications");
}

export function fetchWorkstations(): Promise<Workstation[]> {
  return request<Workstation[]>("/workstations");
}

export function discoverWorkstations(): Promise<DiscoveredVM[]> {
  return request<DiscoveredVM[]>("/workstations/discover");
}

export function pushWorkstation(payload: {
  ip?: string;
  vm_name?: string;
  ssh_port?: number;
  ssh_user?: string;
  reviewer_initials: string;
}): Promise<Workstation> {
  return request<Workstation>("/workstations/push", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function revokeWorkstation(
  id: string,
  reviewer_initials: string
): Promise<Workstation> {
  return request<Workstation>(`/workstations/${id}/revoke`, {
    method: "POST",
    body: JSON.stringify({ reviewer_initials }),
  });
}
