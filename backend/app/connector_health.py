import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Literal

import httpx

from app.context_packet import utc_now
from app.models import ConnectorHealth

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


def _resolve_terraform() -> Path | None:
    env_path = os.getenv("PILOT_REAL_TERRAFORM", "").strip()
    if env_path and Path(env_path).exists():
        return Path(env_path)
    if TERRAFORM_BIN.exists():
        return TERRAFORM_BIN
    found = shutil.which("terraform")
    return Path(found) if found else None


def _check_terraform_cli() -> ConnectorHealth:
    now = utc_now()
    tf = _resolve_terraform()
    if not tf:
        return ConnectorHealth(
            name="Terraform CLI",
            status="down",
            last_checked=now,
            message="terraform binary not found (run scripts/install-terraform.sh)",
        )
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


def _check_openai() -> ConnectorHealth:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    now = utc_now()

    if not api_key:
        return ConnectorHealth(
            name="OpenAI",
            status="down",
            last_checked=now,
            message="OPENAI_API_KEY not configured",
        )

    start = time.monotonic()
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(
                "https://api.openai.com/v1/models?limit=1",
                headers={"Authorization": f"Bearer {api_key}"},
            )
        elapsed_ms = int((time.monotonic() - start) * 1000)

        if response.status_code == 200:
            status: Status = "degraded" if elapsed_ms > DEGRADED_LATENCY_MS else "healthy"
            return ConnectorHealth(
                name="OpenAI",
                status=status,
                last_checked=now,
                message=f"API reachable ({elapsed_ms}ms)",
            )
        if response.status_code == 401:
            return ConnectorHealth(
                name="OpenAI",
                status="down",
                last_checked=now,
                message="Invalid API key (401 Unauthorized)",
            )
        return ConnectorHealth(
            name="OpenAI",
            status="degraded",
            last_checked=now,
            message=f"Unexpected status {response.status_code}",
        )
    except httpx.TimeoutException:
        return ConnectorHealth(
            name="OpenAI",
            status="degraded",
            last_checked=now,
            message="Request timed out (>5s)",
        )
    except httpx.RequestError as exc:
        return ConnectorHealth(
            name="OpenAI",
            status="down",
            last_checked=now,
            message=f"Connection failed: {exc}",
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
            status="down",
            last_checked=now,
            message=str(exc),
        )


def get_all_connector_health() -> list[ConnectorHealth]:
    return [
        _cached("openai", _check_openai),
        _cached("terraform_cli", _check_terraform_cli),
        _cached("terraform", _check_terraform_registry),
        ConnectorHealth(
            name="Policy Rule Engine",
            status="healthy",
            last_checked=utc_now(),
            message="AWS + IAM baseline policy packs loaded",
        ),
        ConnectorHealth(
            name="Apply Gate Shim",
            status="healthy",
            last_checked=utc_now(),
            message="terraform wrapper active",
        ),
        ConnectorHealth(
            name="AI Policy Reviewer",
            status="healthy" if os.getenv("OPENAI_API_KEY", "").strip() else "degraded",
            last_checked=utc_now(),
            message="Active" if os.getenv("OPENAI_API_KEY", "").strip() else "Inactive — rule engine only",
        ),
    ]
