import os
import socket

from app.models import AgentStatus, DiscoveredVM, WorkstationState
from app.store import find_workstation_by_ip_or_name, list_workstations

DEFAULT_SSH_PORT = int(os.getenv("PILOT_WORKSTATION_SSH_PORT", "22"))
PROBE_TIMEOUT = float(os.getenv("PILOT_PROBE_TIMEOUT", "2"))


def _known_workstation_hosts() -> list[str]:
    raw = os.getenv("PILOT_KNOWN_WORKSTATIONS", "pilot-dev")
    return [h.strip() for h in raw.split(",") if h.strip()]


def _probe_tcp(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=PROBE_TIMEOUT):
            return True
    except OSError:
        return False


def _find_fleet_match(
    fleet: list,
    *,
    hostname: str = "",
):
    ws = find_workstation_by_ip_or_name(ip=hostname, vm_name=hostname)
    if ws:
        return ws
    for item in fleet:
        if hostname and (item.vm_name == hostname or item.hostname == hostname or item.ip == hostname):
            return item
    return None


def _deploy_state_for(ws, *, reachable: bool) -> WorkstationState:
    if not ws:
        return WorkstationState.PENDING_PUSH
    if reachable and ws.state in (WorkstationState.FAILED, WorkstationState.REVOKED):
        return WorkstationState.PENDING_PUSH
    return ws.state


def discover_workstations() -> list[DiscoveredVM]:
    """Discover developer workstations on the shared network.

    No Docker/orchestrator API access — discovery uses:
    1. Self-registration beacons (POST /api/workstations/register)
    2. TCP reachability probe to known workstation hostnames (port 22)
    3. Agent heartbeat state from the fleet store
    """
    fleet = list_workstations()
    discovered: list[DiscoveredVM] = []
    seen_hosts: set[str] = set()
    seen_ws_ids: set[str] = set()

    candidates = {h for h in _known_workstation_hosts()}
    for ws in fleet:
        for name in (ws.vm_name, ws.hostname, ws.ip):
            if name:
                candidates.add(name)

    def _sort_key(host: str) -> tuple[int, str]:
        # Prefer service DNS names over loopback IPs
        is_ip = host.replace(".", "").isdigit() or host in ("127.0.0.1", "localhost")
        return (1 if is_ip else 0, host)

    for hostname in sorted(candidates, key=_sort_key):
        if hostname in seen_hosts:
            continue

        ws = _find_fleet_match(fleet, hostname=hostname)
        if ws and ws.id in seen_ws_ids:
            continue

        seen_hosts.add(hostname)
        if ws:
            seen_ws_ids.add(ws.id)

        reachable = _probe_tcp(hostname, DEFAULT_SSH_PORT)
        port = DEFAULT_SSH_PORT
        if ws and ws.ssh_port and ws.ssh_port not in (2222,):
            port = ws.ssh_port

        if ws:
            discovery_source = ws.discovery_source or "heartbeat"
        elif reachable:
            discovery_source = "network-probe"
        else:
            discovery_source = "unreachable"

        discovered.append(
            DiscoveredVM(
                vm_name=ws.vm_name if ws and ws.vm_name else hostname,
                ip=hostname,
                ssh_port=port,
                container_id=ws.container_id if ws else "",
                endpoint=f"{hostname}:{port}",
                discovery_source=discovery_source,
                state="Running" if reachable else "Unreachable",
                workstation_id=ws.id if ws else None,
                agent_status=ws.agent_status if ws else AgentStatus.NOT_DEPLOYED,
                deploy_state=_deploy_state_for(ws, reachable=reachable),
            )
        )

    return discovered
