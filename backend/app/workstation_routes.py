from fastapi import APIRouter, HTTPException, Query

from app.agent_push import push_to_workstation, revoke_workstation
from app.models import (
    DiscoveredVM,
    HeartbeatRequest,
    PushWorkstationRequest,
    RevokeWorkstationRequest,
    Workstation,
    WorkstationNotification,
    WorkstationState,
)
from app.store import (
    get_workstation,
    list_workstation_notifications,
    list_workstations,
    mark_workstation_notifications_read,
    save_workstation_notification,
    update_workstation,
)
from app.vm_discovery import discover_vms

router = APIRouter(prefix="/api/workstations", tags=["workstations"])


@router.get("/discover", response_model=list[DiscoveredVM])
def discover_workstations() -> list[DiscoveredVM]:
    return discover_vms()


@router.get("", response_model=list[Workstation])
def list_workstations_endpoint() -> list[Workstation]:
    return list_workstations()


@router.get("/{workstation_id}", response_model=Workstation)
def get_workstation_endpoint(workstation_id: str) -> Workstation:
    ws = get_workstation(workstation_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workstation not found")
    return ws


@router.post("/push", response_model=Workstation)
def push_workstation_endpoint(body: PushWorkstationRequest) -> Workstation:
    try:
        result = push_to_workstation(
            ip=body.ip,
            vm_name=body.vm_name,
            ssh_user=body.ssh_user,
            reviewer_initials=body.reviewer_initials,
        )
        ws = get_workstation(result["id"])
        if not ws:
            raise HTTPException(status_code=500, detail="Push succeeded but workstation not found")
        return ws
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{workstation_id}/heartbeat", response_model=Workstation)
def heartbeat_endpoint(workstation_id: str, body: HeartbeatRequest) -> Workstation:
    ws = get_workstation(workstation_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workstation not found")
    if ws.state not in (WorkstationState.DEPLOYED, WorkstationState.DEPLOYING):
        raise HTTPException(status_code=409, detail="Workstation not in deployed state")

    from app.context_packet import utc_now

    updated = update_workstation(
        workstation_id,
        last_seen_at=utc_now(),
        shim_version=body.shim_version,
        gate_active=body.gate_active,
        terraform_path=body.terraform_path,
        hostname=body.hostname or ws.hostname,
        state=WorkstationState.DEPLOYED,
    )
    return updated


@router.get("/{workstation_id}/notifications", response_model=list[WorkstationNotification])
def workstation_notifications_endpoint(
    workstation_id: str,
    unread_only: bool = Query(default=False),
) -> list[WorkstationNotification]:
    ws = get_workstation(workstation_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workstation not found")
    notes = list_workstation_notifications(workstation_id, unread_only=unread_only)
    if unread_only and notes:
        mark_workstation_notifications_read(workstation_id)
    return notes


@router.post("/{workstation_id}/revoke", response_model=Workstation)
def revoke_workstation_endpoint(
    workstation_id: str,
    body: RevokeWorkstationRequest,
) -> Workstation:
    try:
        revoke_workstation(workstation_id, body.reviewer_initials)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    ws = get_workstation(workstation_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workstation not found")
    return ws
