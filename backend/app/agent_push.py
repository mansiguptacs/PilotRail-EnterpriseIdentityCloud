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
from app.vm_discovery import get_vm_ip

REPO_ROOT = Path(__file__).resolve().parents[2]
SHIM_VERSION = "0.1.0"
SSH_KEY = REPO_ROOT / "demo-vm" / "keys" / "pilot_push_key"
PUSH_TRANSPORT = os.getenv("PUSH_TRANSPORT", "auto")


def detect_host_api_url() -> str:
    env_url = os.getenv("PILOT_HOST_API_URL", "").strip()
    if env_url:
        return env_url.rstrip("/")
    try:
        script = REPO_ROOT / "scripts" / "host-api-url.sh"
        if script.exists():
            result = subprocess.run(
                [str(script)],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().rstrip("/")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return "http://127.0.0.1:8000"


def _multipass_available() -> bool:
    return shutil.which("multipass") is not None


def _run(cmd: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def _multipass_exec(vm_name: str, remote_cmd: str) -> None:
    result = _run(["multipass", "exec", vm_name, "--", "bash", "-lc", remote_cmd])
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout or "multipass exec failed")


def _multipass_transfer(local: Path, vm_name: str, remote: str) -> None:
    result = _run(["multipass", "transfer", str(local), f"{vm_name}:{remote}"])
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout or "multipass transfer failed")


def _ssh_exec(ip: str, user: str, remote_cmd: str) -> None:
    if not SSH_KEY.exists():
        raise RuntimeError(f"SSH key not found: {SSH_KEY}")
    cmd = [
        "ssh",
        "-i", str(SSH_KEY),
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        f"{user}@{ip}",
        remote_cmd,
    ]
    result = _run(cmd)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout or "ssh exec failed")


def _scp_to(ip: str, user: str, local: Path, remote: str) -> None:
    if not SSH_KEY.exists():
        raise RuntimeError(f"SSH key not found: {SSH_KEY}")
    cmd = [
        "scp",
        "-i", str(SSH_KEY),
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-r", str(local), f"{user}@{ip}:{remote}",
    ]
    result = _run(cmd, timeout=180)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout or "scp failed")


def _build_bundle() -> Path:
    # multipass (snap) cannot read arbitrary /tmp paths — stage under repo
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


def push_to_workstation(
    ip: str,
    vm_name: str,
    ssh_user: str,
    reviewer_initials: str,
) -> dict:
    if vm_name and not ip:
        ip = get_vm_ip(vm_name) or ""
    if not ip and not vm_name:
        raise ValueError("ip or vm_name required")

    ws = create_workstation(ip=ip, vm_name=vm_name, ssh_user=ssh_user)
    update_workstation(ws.id, state=WorkstationState.DEPLOYING, last_error=None)

    host_api = detect_host_api_url()
    bundle = _build_bundle()
    install_cmd = _remote_install_cmd(host_api, ws.id, reviewer_initials)

    try:
        use_multipass = (
            PUSH_TRANSPORT == "multipass"
            or (PUSH_TRANSPORT == "auto" and vm_name and _multipass_available())
        )
        if use_multipass and vm_name:
            _multipass_transfer(bundle, vm_name, "/home/ubuntu/pilot-rail-bundle.tar.gz")
            _multipass_exec(vm_name, install_cmd)
        else:
            _scp_to(ip, ssh_user, bundle, "~/pilot-rail-bundle.tar.gz")
            _ssh_exec(ip, ssh_user, install_cmd)

        update_workstation(
            ws.id,
            state=WorkstationState.DEPLOYED,
            deployed_by=reviewer_initials,
            deployed_at=utc_now(),
            shim_version=SHIM_VERSION,
            gate_active=True,
            hostname=vm_name or ip,
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
            comment=f"Deployed to {ip or vm_name}",
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
    try:
        if ws.vm_name and _multipass_available():
            _multipass_exec(ws.vm_name, stop_cmd)
        elif ws.ip:
            _ssh_exec(ws.ip, ws.ssh_user, stop_cmd)
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
        comment=f"Revoked on {ws.ip or ws.vm_name}",
    )
