import json
import re
import shutil
import subprocess

from app.models import AgentStatus, DiscoveredVM, WorkstationState
from app.store import find_workstation_by_ip_or_name, list_workstations

MANAGED_LABEL = "pilot-rail.io/managed=true"
DEFAULT_SSH_PORT = 2222
DEFAULT_IP = "127.0.0.1"


def _docker_available() -> bool:
    return shutil.which("docker") is not None


def _parse_host_ssh_port(ports: str) -> int:
    if not ports:
        return DEFAULT_SSH_PORT
    match = re.search(r":(\d+)->22", ports)
    if match:
        return int(match.group(1))
    match = re.search(r"^(\d+)->22", ports)
    if match:
        return int(match.group(1))
    return DEFAULT_SSH_PORT


def list_managed_containers() -> list[dict]:
    if not _docker_available():
        return []
    try:
        result = subprocess.run(
            [
                "docker",
                "ps",
                "--filter",
                f"label={MANAGED_LABEL}",
                "--format",
                "{{json .}}",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            return []
        containers: list[dict] = []
        for line in result.stdout.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                containers.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return containers
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


def _find_fleet_match(
    fleet: list,
    *,
    vm_name: str = "",
    ip: str = "",
    container_id: str = "",
):
    ws = find_workstation_by_ip_or_name(ip=ip, vm_name=vm_name)
    if ws:
        return ws
    for item in fleet:
        cid = getattr(item, "container_id", "") or ""
        if container_id and cid and (
            cid.startswith(container_id[:12]) or container_id.startswith(cid[:12])
        ):
            return item
        if vm_name and (item.vm_name == vm_name or item.hostname == vm_name):
            return item
    return None


def discover_workstations() -> list[DiscoveredVM]:
    fleet = list_workstations()
    discovered: list[DiscoveredVM] = []
    seen_names: set[str] = set()

    for entry in list_managed_containers():
        name = entry.get("Names", "").lstrip("/")
        if not name:
            continue
        state = entry.get("State", "unknown")
        if state.lower() != "running":
            continue

        container_id = (entry.get("ID") or "")[:12]
        ports = entry.get("Ports", "") or entry.get("LocalPorts", "")
        ssh_port = _parse_host_ssh_port(ports)
        ip = DEFAULT_IP
        endpoint = f"{ip}:{ssh_port}"

        ws = _find_fleet_match(fleet, vm_name=name, ip=ip, container_id=container_id)
        discovery_source = "label-scan"
        if ws and getattr(ws, "discovery_source", "") == "self-registered":
            discovery_source = "self-registered"

        discovered.append(
            DiscoveredVM(
                vm_name=name,
                ip=ip,
                ssh_port=ssh_port,
                container_id=container_id,
                endpoint=endpoint,
                discovery_source=discovery_source,
                state=state,
                workstation_id=ws.id if ws else None,
                agent_status=ws.agent_status if ws else AgentStatus.NOT_DEPLOYED,
                deploy_state=ws.state if ws else WorkstationState.PENDING_PUSH,
            )
        )
        seen_names.add(name)

    for ws in fleet:
        if ws.vm_name and ws.vm_name in seen_names:
            continue
        port = ws.ssh_port or DEFAULT_SSH_PORT
        discovered.append(
            DiscoveredVM(
                vm_name=ws.vm_name or ws.hostname,
                ip=ws.ip or DEFAULT_IP,
                ssh_port=port,
                container_id=ws.container_id,
                endpoint=f"{ws.ip}:{port}" if ws.ip else "",
                discovery_source=ws.discovery_source or "heartbeat",
                state="unknown",
                workstation_id=ws.id,
                agent_status=ws.agent_status,
                deploy_state=ws.state,
            )
        )

    return discovered
