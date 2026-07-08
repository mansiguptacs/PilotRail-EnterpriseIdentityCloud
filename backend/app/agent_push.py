import os
import shlex
import subprocess
import tarfile
from pathlib import Path

from app.context_packet import utc_now
from app.models import PlanState, WorkstationState
from app.store import (
    append_audit,
    create_workstation,
    get_workstation,
    save_workstation_notification,
    update_workstation,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SHIM_VERSION = "0.1.0"
SSH_KEY = REPO_ROOT / "demo-vm" / "keys" / "pilot_push_key"
DEFAULT_SSH_USER = "developer"
DEFAULT_SSH_PORT = int(os.getenv("PILOT_WORKSTATION_SSH_PORT", "22"))
PUSH_TRANSPORT = os.getenv("PUSH_TRANSPORT", "ssh")


def detect_container_api_url() -> str:
    env_url = os.getenv("PILOT_HOST_API_URL", "").strip()
    if env_url:
        return env_url.rstrip("/")
    return "http://host.docker.internal:8000"


def _run(cmd: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def _resolve_ssh_target(ip: str, vm_name: str, ssh_port: int) -> tuple[str, int]:
    """Resolve SSH host/port on the shared pod/network (not host-mapped ports)."""
    host = (vm_name or ip or "").strip()
    if not host:
        raise ValueError("Workstation hostname or ip required for SSH push")

    port = ssh_port or DEFAULT_SSH_PORT
    # Legacy UI may send 127.0.0.1:2222 — prefer service DNS on internal network
    if vm_name and ip in ("", "127.0.0.1", "localhost"):
        host = vm_name
        if port in (2222, 0):
            port = DEFAULT_SSH_PORT

    return host, port


def _ssh_exec(host: str, user: str, remote_cmd: str, port: int) -> None:
    if not SSH_KEY.exists():
        raise RuntimeError(f"SSH key not found: {SSH_KEY}")
    cmd = [
        "ssh",
        "-i",
        str(SSH_KEY),
        "-p",
        str(port),
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        f"{user}@{host}",
        remote_cmd,
    ]
    result = _run(cmd, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout or "ssh exec failed")


def _scp_to(host: str, user: str, local: Path, remote: str, port: int) -> None:
    if not SSH_KEY.exists():
        raise RuntimeError(f"SSH key not found: {SSH_KEY}")
    cmd = [
        "scp",
        "-i",
        str(SSH_KEY),
        "-P",
        str(port),
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        str(local),
        f"{user}@{host}:{remote}",
    ]
    result = _run(cmd, timeout=180)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout or "scp failed")


def _build_bundle() -> Path:
    staging = REPO_ROOT / "demo-vm" / "staging"
    staging.mkdir(parents=True, exist_ok=True)
    bundle = staging / "pilot-rail-bundle.tar.gz"
    paths_to_add = [
        ("cli/shim/terraform", "shim/terraform"),
        ("cli/agent/pilot-rail-agent", "agent/pilot-rail-agent"),
        ("cli/agent/pilot-rail-show-notice", "agent/pilot-rail-show-notice"),
        ("cli/agent/remote-install.sh", "agent/remote-install.sh"),
    ]
    with tarfile.open(bundle, "w:gz") as tar:
        for src_rel, arcname in paths_to_add:
            src = REPO_ROOT / src_rel
            if src.exists():
                tar.add(src, arcname=arcname)
        demo_ws = REPO_ROOT / "demo-workspace"
        if demo_ws.exists():
            for item in demo_ws.iterdir():
                if item.name.startswith("."):
                    continue
                tar.add(item, arcname=f"workspace/{item.name}")
    return bundle


def _remote_install_cmd(host_api: str, workstation_id: str, deployed_by: str) -> str:
    env = (
        f"PILOT_API_BASE={shlex.quote(host_api + '/api')} "
        f"WORKSTATION_ID={shlex.quote(workstation_id)} "
        f"DEPLOYED_BY={shlex.quote(deployed_by)} "
        f"SHIM_VERSION={SHIM_VERSION}"
    )
    return (
        f"mkdir -p ~/.pilot-rail && "
        f"tar -xzf ~/pilot-rail-bundle.tar.gz -C ~/.pilot-rail && "
        f"chmod +x ~/.pilot-rail/agent/remote-install.sh && "
        f"{env} bash ~/.pilot-rail/agent/remote-install.sh"
    )


def _push_bundle(
    *,
    host: str,
    ssh_user: str,
    ssh_port: int,
    bundle: Path,
    install_cmd: str,
) -> None:
    if PUSH_TRANSPORT != "ssh":
        raise RuntimeError(
            f"Unsupported PUSH_TRANSPORT={PUSH_TRANSPORT!r}. "
            "Admin pod pushes to developer workstations over SSH on the shared network."
        )
    _scp_to(host, ssh_user, bundle, "~/pilot-rail-bundle.tar.gz", port=ssh_port)
    _ssh_exec(host, ssh_user, install_cmd, port=ssh_port)


def push_to_workstation(
    ip: str,
    vm_name: str,
    ssh_user: str,
    ssh_port: int,
    reviewer_initials: str,
) -> dict:
    if not ssh_user:
        ssh_user = DEFAULT_SSH_USER
    if not ip and not vm_name:
        raise ValueError("ip or vm_name (workstation hostname) required")

    host, port = _resolve_ssh_target(ip, vm_name, ssh_port)

    ws = create_workstation(
        ip=host,
        vm_name=vm_name or host,
        hostname=vm_name or host,
        ssh_user=ssh_user,
    )
    update_workstation(
        ws.id,
        state=WorkstationState.DEPLOYING,
        ssh_port=port,
        last_error=None,
    )

    host_api = detect_container_api_url()
    bundle = _build_bundle()
    install_cmd = _remote_install_cmd(host_api, ws.id, reviewer_initials)

    try:
        _push_bundle(
            host=host,
            ssh_user=ssh_user,
            ssh_port=port,
            bundle=bundle,
            install_cmd=install_cmd,
        )

        update_workstation(
            ws.id,
            state=WorkstationState.DEPLOYED,
            deployed_by=reviewer_initials,
            deployed_at=utc_now(),
            shim_version=SHIM_VERSION,
            gate_active=True,
            hostname=vm_name or host,
            last_error=None,
        )
        save_workstation_notification(
            ws.id,
            f"IT admin ({reviewer_initials}) deployed the Pilot Rail apply gate. "
            f"terraform apply is now governed. Control plane: {host_api}",
            event_type="NOTIFY_WORKSTATION",
        )
        append_audit(
            plan_id=ws.id,
            action="AGENT_PUSH",
            reviewer_initials=reviewer_initials,
            previous_state=PlanState.PENDING_REVIEW,
            new_state=PlanState.PENDING_REVIEW,
            comment=f"Deployed via SSH to {host}:{port}",
        )
        return get_workstation(ws.id).model_dump(mode="json")  # type: ignore[union-attr]
    except Exception as exc:
        update_workstation(ws.id, state=WorkstationState.FAILED, last_error=str(exc))
        raise


def revoke_workstation(workstation_id: str, reviewer_initials: str) -> None:
    ws = get_workstation(workstation_id)
    if not ws:
        raise KeyError(f"Workstation {workstation_id} not found")

    host, port = _resolve_ssh_target(ws.ip, ws.vm_name, ws.ssh_port)
    stop_cmd = (
        'if [[ -f ~/.pilot-rail/agent.pid ]]; then kill "$(cat ~/.pilot-rail/agent.pid)" 2>/dev/null; fi; '
        'sed -i "/pilot-rail/d" ~/.bashrc 2>/dev/null || true'
    )
    try:
        _ssh_exec(host, ws.ssh_user or DEFAULT_SSH_USER, stop_cmd, port)
    except Exception:
        pass

    update_workstation(
        workstation_id,
        state=WorkstationState.REVOKED,
        gate_active=False,
    )
    append_audit(
        plan_id=workstation_id,
        action="AGENT_REVOKE",
        reviewer_initials=reviewer_initials,
        previous_state=PlanState.APPROVED,
        new_state=PlanState.REJECTED,
        comment=f"Revoked on {host}:{port}",
    )
