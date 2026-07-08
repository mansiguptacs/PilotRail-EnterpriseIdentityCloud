import type { AuditEntry, ConnectorHealth, Notification, Plan } from "./types";

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
