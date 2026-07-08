import json
import shutil
import subprocess
from typing import Optional

from app.models import AgentStatus, DiscoveredVM, WorkstationState
from app.store import find_workstation_by_ip_or_name, list_workstations


def _multipass_available() -> bool:
    return shutil.which("multipass") is not None


def list_multipass_vms() -> list[dict]:
    if not _multipass_available():
        return []
    try:
        result = subprocess.run(
            ["multipass", "list", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            return []
        data = json.loads(result.stdout)
        raw = data.get("list", []) if isinstance(data, dict) else []
        if isinstance(raw, list):
            return raw
        if isinstance(raw, dict):
            # Older multipass: {"list": {"vm-name": {...}}}
            return [{"name": name, **info} for name, info in raw.items()]
        return []
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        return []


def get_vm_ip(vm_name: str) -> Optional[str]:
    if not _multipass_available():
        return None
    try:
        result = subprocess.run(
            ["multipass", "info", vm_name, "--format", "json"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout)
        ipv4 = data.get("info", {}).get(vm_name, {}).get("ipv4", [])
        return ipv4[0] if ipv4 else None
    except (subprocess.TimeoutExpired, json.JSONDecodeError, IndexError, KeyError):
        return None


def discover_vms() -> list[DiscoveredVM]:
    fleet = list_workstations()
    discovered: list[DiscoveredVM] = []

    for entry in list_multipass_vms():
        name = entry.get("name", "")
        state = entry.get("state", "unknown")
        if state != "Running":
            continue
        ipv4 = entry.get("ipv4", [])
        ip = ipv4[0] if ipv4 else (get_vm_ip(name) or "")
        if not ip:
            continue
        ws = find_workstation_by_ip_or_name(ip=ip, vm_name=name)
        discovered.append(
            DiscoveredVM(
                vm_name=name,
                ip=ip,
                state=state,
                workstation_id=ws.id if ws else None,
                agent_status=ws.agent_status if ws else AgentStatus.NOT_DEPLOYED,
                deploy_state=ws.state if ws else WorkstationState.PENDING_PUSH,
            )
        )

    known_ips = {d.ip for d in discovered}
    for ws in fleet:
        if ws.ip and ws.ip not in known_ips:
            discovered.append(
                DiscoveredVM(
                    vm_name=ws.vm_name,
                    ip=ws.ip,
                    state="unknown",
                    workstation_id=ws.id,
                    agent_status=ws.agent_status,
                    deploy_state=ws.state,
                )
            )

    return discovered
