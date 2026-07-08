export type PlanState = "PENDING_REVIEW" | "APPROVED" | "REJECTED" | "AUTO_APPROVED";

export interface PolicyFinding {
  policy_id: string;
  term: string;
  line_number: number;
  severity: string;
  category: string;
  message: string;
  remediation: string;
  source: string;
  matched_text: string;
}

export interface PilotGuidance {
  message: string;
  suggestion: string;
}

export interface Plan {
  id: string;
  prompt: string;
  code: string;
  reasoning: string;
  state: PlanState;
  security_warning: boolean;
  findings: PolicyFinding[];
  model: string;
  scan_model: string;
  pilot_guidance: PilotGuidance;
  requester: string;
  source: string;
  risk_tier: string;
  enforcement_level: string;
  plan_fingerprint: string;
  workspace_path: string;
  execution_status: string;
  execution_output: string | null;
  execution_exit_code: number | null;
  reviewer_initials: string | null;
  reject_comment: string | null;
  context_packet_hash: string;
  created_at: string;
  updated_at: string;
}

export interface AuditEntry {
  id: string;
  plan_id: string;
  action: string;
  reviewer_initials: string;
  comment: string | null;
  previous_state: PlanState;
  new_state: PlanState;
  timestamp: string;
}

export interface Notification {
  id: string;
  plan_id: string;
  recipient: string;
  channel: string;
  message: string;
  event_type: string;
  timestamp: string;
}

export interface ConnectorHealth {
  name: string;
  status: string;
  last_checked: string;
  message: string;
}
