import time

_last_success_at: float | None = None
_last_failure_at: float | None = None
_last_error: str = ""


def record_grok_success() -> None:
    global _last_success_at
    _last_success_at = time.monotonic()


def record_grok_failure(message: str) -> None:
    global _last_failure_at, _last_error
    _last_failure_at = time.monotonic()
    _last_error = message[:240]


def grok_runtime_status() -> tuple[str, str]:
    """Return (status, message) based on real policy-scan usage — no API probe."""
    if _last_success_at is not None and (
        _last_failure_at is None or _last_success_at >= _last_failure_at
    ):
        ago_s = int(time.monotonic() - _last_success_at)
        if ago_s < 60:
            return "healthy", f"Active — last review {ago_s}s ago"
        if ago_s < 3600:
            return "healthy", f"Active — last review {ago_s // 60}m ago"
        return "healthy", f"Active — last review {ago_s // 3600}h ago"

    if _last_failure_at is not None and (
        _last_success_at is None or _last_failure_at > _last_success_at
    ):
        return "degraded", f"Last review failed — {_last_error or 'see backend logs'}"

    return "healthy", "Configured — verified on policy scan (no idle API probes)"
