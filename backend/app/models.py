from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


class PlanState(str, Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    AUTO_APPROVED = "AUTO_APPROVED"


class PolicyFinding(BaseModel):
    policy_id: str = "UNKNOWN"
    term: str
    line_number: int
    severity: str
    category: str = "compliance"
    message: str
    remediation: str = ""
    source: str = "rule_engine"
    matched_text: str = ""


class PilotGuidance(BaseModel):
    message: str
    suggestion: str = ""


class ScanResult(BaseModel):
    findings: list[PolicyFinding]
    security_warning: bool
    pilot_guidance: PilotGuidance
    scan_model: str = "none"
    risk_tier: str = "none"
    enforcement_level: str = "advisory"
    recommended_state: PlanState = PlanState.PENDING_REVIEW


class ContextPacket(BaseModel):
    plan_id: str
    prompt: str
    model: str
    reasoning: str
    findings: list[PolicyFinding]
    state: PlanState
    created_at: str
    integrity_hash: str


class Plan(BaseModel):
    id: str
    prompt: str
    code: str
    reasoning: str
    state: PlanState
    security_warning: bool
    findings: list[PolicyFinding]
    model: str
    scan_model: str = "none"
    pilot_guidance: PilotGuidance = Field(default_factory=lambda: PilotGuidance(message=""))
    requester: str = "unknown"
    source: str = "ui"
    risk_tier: str = "none"
    enforcement_level: str = "advisory"
    plan_fingerprint: str = ""
    workspace_path: str = ""
    execution_status: str = "not_started"
    execution_output: Optional[str] = None
    execution_exit_code: Optional[int] = None
    reviewer_initials: Optional[str] = None
    reject_comment: Optional[str] = None
    context_packet_hash: str
    created_at: str
    updated_at: str


class AuditEntry(BaseModel):
    id: str
    plan_id: str
    action: str
    reviewer_initials: str
    comment: Optional[str] = None
    previous_state: PlanState
    new_state: PlanState
    timestamp: str


class Notification(BaseModel):
    id: str
    plan_id: str
    recipient: str
    channel: str
    message: str
    event_type: str
    timestamp: str


class CreatePlanRequest(BaseModel):
    prompt: Optional[str] = None
    code: Optional[str] = None
    plan_json: Optional[str] = None
    plan_fingerprint: Optional[str] = None
    workspace_path: str = ""
    requester: str = "unknown"
    source: Literal["wrapper", "agent", "ui"] = "ui"

    @model_validator(mode="after")
    def require_prompt_or_code(self):
        if not self.prompt and not self.code:
            raise ValueError("Either prompt or code must be provided")
        return self


class ApproveRequest(BaseModel):
    reviewer_initials: str = Field(..., min_length=1)


class RejectRequest(BaseModel):
    reviewer_initials: str = Field(..., min_length=1)
    comment: str = Field(..., min_length=1)


class ExecutionReport(BaseModel):
    status: Literal["running", "succeeded", "failed"]
    output: str = ""
    exit_code: int = 0


class ConnectorHealth(BaseModel):
    name: str
    status: str
    last_checked: str
    message: str


class WorkstationState(str, Enum):
    PENDING_PUSH = "PENDING_PUSH"
    DEPLOYING = "DEPLOYING"
    DEPLOYED = "DEPLOYED"
    FAILED = "FAILED"
    REVOKED = "REVOKED"


class AgentStatus(str, Enum):
    NOT_DEPLOYED = "NOT_DEPLOYED"
    ONLINE = "ONLINE"
    STALE = "STALE"
    OFFLINE = "OFFLINE"


class Workstation(BaseModel):
    id: str
    ip: str
    hostname: str = ""
    vm_name: str = ""
    ssh_user: str = "developer"
    state: WorkstationState = WorkstationState.PENDING_PUSH
    agent_status: AgentStatus = AgentStatus.NOT_DEPLOYED
    last_seen_at: Optional[str] = None
    shim_version: str = ""
    gate_active: bool = False
    terraform_path: str = ""
    deployed_by: Optional[str] = None
    deployed_at: Optional[str] = None
    last_error: Optional[str] = None
    container_id: str = ""
    ssh_port: int = 2222
    discovery_source: str = ""
    created_at: str
    updated_at: str


class WorkstationNotification(BaseModel):
    id: str
    workstation_id: str
    message: str
    event_type: str
    read: bool = False
    timestamp: str


class DiscoveredVM(BaseModel):
    vm_name: str
    ip: str
    ssh_port: int = 2222
    container_id: str = ""
    endpoint: str = ""
    discovery_source: str = "label-scan"
    state: str
    workstation_id: Optional[str] = None
    agent_status: AgentStatus = AgentStatus.NOT_DEPLOYED
    deploy_state: WorkstationState = WorkstationState.PENDING_PUSH


class PushWorkstationRequest(BaseModel):
    ip: str = ""
    vm_name: str = ""
    ssh_port: int = 0
    ssh_user: str = "developer"
    reviewer_initials: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def require_target(self):
        if not self.ip and not self.vm_name:
            raise ValueError("Either ip or vm_name must be provided")
        return self




class RegisterWorkstationRequest(BaseModel):
    hostname: str
    container_id: str = ""
    host_ssh_port: int = 2222
    ip: str = "127.0.0.1"

class HeartbeatRequest(BaseModel):
    shim_version: str = "0.1.0"
    agent_version: str = "0.1.0"
    gate_active: bool = True
    hostname: str = ""
    terraform_path: str = ""


class RevokeWorkstationRequest(BaseModel):
    reviewer_initials: str = Field(..., min_length=1)
