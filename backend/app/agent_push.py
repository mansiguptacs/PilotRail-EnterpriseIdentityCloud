import os
import shlex
import shutil
import subprocess
import tarfile
from pathlib import Path

from app.context_packet import utc_now
from app.models import AgentStatus, PlanState, WorkstationState
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
DEFAULT_SSH_PORT = 2222
DEFAULT_SSH_USER = "developer"
REMOTE_BUNDLE = "/home/developer/pilot-rail-bundle.tar.gz"
PUSH_TRANSPORT = os.getenv("PUSH_TRANSPORT", "auto")


def detect_container_api_url() -> str:
    env_url = os.getenv("PILOT_HOST_API_URL", "").strip()
    if env_url:
        return env_url.rstrip("/")
    return "http://host.docker.internal:8000"


def _docker_available() -> bool:
    return shutil.which("docker") is not None


def _run(cmd: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def _ssh_exec(ip: str, user: str, remote_cmd: str, port: int = 22) -> None:
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
        f"{user}@{ip}",
        remote_cmd,
    ]
    result = _run(cmd)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout or "ssh exec failed")


def _scp_to(ip: str, user: str, local: Path, remote: str, port: int = 22) -> None:
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
        f"{user}@{ip}:{remote}",
    ]
    result = _run(cmd, timeout=180)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout or "scp failed")


def _docker_exec(container: str, remote_cmd: str, user: str = DEFAULT_SSH_USER) -> None:
    result = _run(
        ["docker", "exec", "-u", user, container, "bash", "-lc", remote_cmd],
        timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout or "docker exec failed")


def _docker_cp(local: Path, container: str, remote: str) -> None:
    result = _run(["docker", "cp", str(local), f"{container}:{remote}"], timeout=180)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout or "docker cp failed")


def _try_ssh_push(
    ip: str,
    user: str,
    port: int,
    bundle: Path,
    install_cmd: str,
) -> bool:
    try:
        _scp_to(ip, user, bundle, "~/pilot-rail-bundle.tar.gz", port=port)
        _ssh_exec(ip, user, install_cmd, port=port)
        return True
    except Exception:
        return False


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
    ip: str,
    container_name: str,
    ssh_user: str,
    ssh_port: int,
    bundle: Path,
    install_cmd: str,
) -> None:
    if PUSH_TRANSPORT == "docker":
        if not container_name:
            raise RuntimeError("container name required for docker push transport")
        _docker_cp(bundle, container_name, REMOTE_BUNDLE)
        _docker_exec(container_name, install_cmd, user=ssh_user)
        return

    if PUSH_TRANSPORT == "ssh":
        _scp_to(ip, ssh_user, bundle, "~/pilot-rail-bundle.tar.gz", port=ssh_port)
        _ssh_exec(ip, ssh_user, install_cmd, port=ssh_port)
        return

    # auto: SSH first, docker exec fallback for managed containers
    if container_name and _try_ssh_push(ip, ssh_user, ssh_port, bundle, install_cmd):
        return
    if container_name and _docker_available():
        _docker_cp(bundle, container_name, REMOTE_BUNDLE)
        _docker_exec(container_name, install_cmd, user=ssh_user)
        return
    if ip:
        _scp_to(ip, ssh_user, bundle, "~/pilot-rail-bundle.tar.gz", port=ssh_port)
        _ssh_exec(ip, ssh_user, install_cmd, port=ssh_port)
        return
    raise RuntimeError("No reachable push target (SSH and docker both failed)")


def _revoke_remote(
    *,
    ip: str,
    container_name: str,
    ssh_user: str,
    ssh_port: int,
    stop_cmd: str,
) -> None:
    if container_name and _docker_available():
        try:
            _docker_exec(container_name, stop_cmd, user=ssh_user)
            return
        except Exception:
            pass
    if ip:
        try:
            _ssh_exec(ip, ssh_user, stop_cmd, port=ssh_port)
        except Exception:
            pass


def push_to_workstation(
    ip: str,
    vm_name: str,
    ssh_user: str,
    ssh_port: int,
    reviewer_initials: str,
) -> dict:
    container_name = vm_name
    if not ip and container_name:
        ip = "127.0.0.1"
    if not ssh_port:
        ssh_port = DEFAULT_SSH_PORT
    if not ssh_user:
        ssh_user = DEFAULT_SSH_USER
    if not ip and not container_name:
        raise ValueError("ip or vm_name (container name) required")

    ws = create_workstation(
        ip=ip,
        vm_name=container_name,
        hostname=container_name or ip,
        ssh_user=ssh_user,
    )
    update_workstation(
        ws.id,
        state=WorkstationState.DEPLOYING,
        ssh_port=ssh_port,
        last_error=None,
    )

    host_api = detect_container_api_url()
    bundle = _build_bundle()
    install_cmd = _remote_install_cmd(host_api, ws.id, reviewer_initials)

    try:
        _push_bundle(
            ip=ip,
            container_name=container_name,
            ssh_user=ssh_user,
            ssh_port=ssh_port,
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
            hostname=container_name or ip,
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
            comment=f"Deployed to {ip}:{ssh_port} ({container_name or 'manual'})",
        )
        return get_workstation(ws.id).model_dump(mode="json")  # type: ignore[union-attr]
    except Exception as exc:
        update_workstation(ws.id, state=WorkstationState.FAILED, last_error=str(exc))
        raise


def revoke_workstation(workstation_id: str, reviewer_initials: str) -> None:
    ws = get_workstation(workstation_id)
    if not ws:
        raise KeyError(f"Workstation {workstation_id} not found")

    stop_cmd = (
        'if [[ -f ~/.pilot-rail/agent.pid ]]; then kill "$(cat ~/.pilot-rail/agent.pid)" 2>/dev/null; fi; '
        'sed -i "/pilot-rail/d" ~/.bashrc 2>/dev/null || true'
    )
    _revoke_remote(
        ip=ws.ip,
        container_name=ws.vm_name,
        ssh_user=ws.ssh_user or DEFAULT_SSH_USER,
        ssh_port=ws.ssh_port or DEFAULT_SSH_PORT,
        stop_cmd=stop_cmd,
    )

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
        comment=f"Revoked on {ws.ip or ws.vm_name}",
    )
