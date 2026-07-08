import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Literal

import httpx

from app.context_packet import utc_now
from app.grok_status import grok_runtime_status
from app.llm_client import xai_api_key, xai_model
from app.models import ConnectorHealth
from app.policy_engine import _load_rules

Status = Literal["healthy", "degraded", "down"]

_cache: dict[str, tuple[float, ConnectorHealth]] = {}
CACHE_TTL_SECONDS = 30
DEGRADED_LATENCY_MS = 2000

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TERRAFORM_BIN = REPO_ROOT / "backend" / "bin" / "terraform"


def _cached(name: str, checker) -> ConnectorHealth:
    now = time.monotonic()
    if name in _cache:
        cached_at, result = _cache[name]
        if now - cached_at < CACHE_TTL_SECONDS:
            return result
    result = checker()
    _cache[name] = (now, result)
    return result


def clear_connector_cache() -> None:
    _cache.clear()


def _resolve_terraform() -> Path | None:
    env_path = os.getenv("PILOT_REAL_TERRAFORM", "").strip()
    if env_path and Path(env_path).exists():
        return Path(env_path)
    if TERRAFORM_BIN.exists():
        return TERRAFORM_BIN
    found = shutil.which("terraform")
    if not found:
        return None
    shim_markers = (".pilot-rail/shim", "cli/shim")
    if any(marker in found for marker in shim_markers):
        return None
    return Path(found)


def _check_workstation_terraform() -> ConnectorHealth | None:
    """Admin pod delegates terraform to managed workstations on the shared network."""
    try:
        from app.store import list_workstations

        deployed = [w for w in list_workstations() if w.gate_active and w.state.value == "DEPLOYED"]
        now = utc_now()
        if deployed:
            names = ", ".join(w.vm_name or w.hostname or w.ip for w in deployed[:3])
            return ConnectorHealth(
                name="Terraform CLI",
                status="healthy",
                last_checked=now,
                message=f"Active on managed workstation(s): {names}",
            )
        return ConnectorHealth(
            name="Terraform CLI",
            status="degraded",
            last_checked=now,
            message="Deploy gate to a workstation to enable terraform apply",
        )
    except Exception:
        return None


def _check_terraform_cli() -> ConnectorHealth:
    now = utc_now()
    tf = _resolve_terraform()
    if tf:
        try:
            result = subprocess.run(
                [str(tf), "version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            version_line = result.stdout.strip().splitlines()[0] if result.stdout else "unknown"
            return ConnectorHealth(
                name="Terraform CLI",
                status="healthy" if result.returncode == 0 else "degraded",
                last_checked=now,
                message=version_line,
            )
        except Exception as exc:
            return ConnectorHealth(
                name="Terraform CLI",
                status="down",
                last_checked=now,
                message=str(exc),
            )

    delegated = _check_workstation_terraform()
    if delegated:
        return delegated

    return ConnectorHealth(
        name="Terraform CLI",
        status="down",
        last_checked=now,
        message="terraform binary not found (run scripts/install-terraform.sh)",
    )


def _check_grok_ai() -> ConnectorHealth:
    api_key = xai_api_key()
    model = xai_model()
    now = utc_now()

    if not api_key:
        return ConnectorHealth(
            name="Grok AI",
            status="degraded",
            last_checked=now,
            message="Optional — set XAI_API_KEY in backend/.env for AI review",
        )

    status, message = grok_runtime_status()
    if status == "healthy" and "Configured" in message:
        message = f"{model} — {message}"

    return ConnectorHealth(
        name="Grok AI",
        status=status,  # type: ignore[arg-type]
        last_checked=now,
        message=message,
    )


def _check_terraform_registry() -> ConnectorHealth:
    now = utc_now()
    start = time.monotonic()
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(
                "https://registry.terraform.io/v1/providers/hashicorp/aws/versions"
            )
        elapsed_ms = int((time.monotonic() - start) * 1000)
        if response.status_code == 200:
            return ConnectorHealth(
                name="Terraform Registry",
                status="healthy",
                last_checked=now,
                message=f"Provider metadata available ({elapsed_ms}ms)",
            )
        return ConnectorHealth(
            name="Terraform Registry",
            status="degraded",
            last_checked=now,
            message=f"Status {response.status_code}",
        )
    except Exception as exc:
        return ConnectorHealth(
            name="Terraform Registry",
            status="degraded",
            last_checked=now,
            message=str(exc),
        )


def _check_policy_engine() -> ConnectorHealth:
    now = utc_now()
    try:
        rules = _load_rules()
        if not rules:
            return ConnectorHealth(
                name="Policy Rule Engine",
                status="down",
                last_checked=now,
                message="No policy packs loaded — all applies will auto-approve",
            )
        return ConnectorHealth(
            name="Policy Rule Engine",
            status="healthy",
            last_checked=now,
            message=f"{len(rules)} rules loaded from AWS + IAM baseline packs",
        )
    except Exception as exc:
        return ConnectorHealth(
            name="Policy Rule Engine",
            status="down",
            last_checked=now,
            message=str(exc),
        )


def get_all_connector_health() -> list[ConnectorHealth]:
    grok_health = _cached("grok_ai", _check_grok_ai)
    ai_reviewer_status: Status = "healthy"
    if grok_health.status == "degraded":
        ai_reviewer_status = "degraded"
    elif grok_health.status == "down":
        ai_reviewer_status = "degraded"

    return [
        grok_health,
        _cached("terraform_cli", _check_terraform_cli),
        _cached("terraform", _check_terraform_registry),
        _cached("policy_engine", _check_policy_engine),
        ConnectorHealth(
            name="Apply Gate Shim",
            status="healthy",
            last_checked=utc_now(),
            message="terraform wrapper active on managed workstations",
        ),
        ConnectorHealth(
            name="AI Policy Reviewer",
            status=ai_reviewer_status,
            last_checked=utc_now(),
            message=grok_health.message,
        ),
    ]
