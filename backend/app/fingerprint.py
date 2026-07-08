import hashlib
import json


def normalize_plan_json(plan_json: str | None) -> str:
    """Strip volatile terraform metadata so re-runs produce the same fingerprint."""
    if not plan_json:
        return ""
    try:
        data = json.loads(plan_json)
    except json.JSONDecodeError:
        return plan_json
    stable = {
        "resource_changes": data.get("resource_changes", []),
        "output_changes": data.get("output_changes", []),
    }
    return json.dumps(stable, sort_keys=True, separators=(",", ":"))


def compute_code_fingerprint(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def compute_plan_fingerprint(
    code: str,
    plan_json: str | None,
    workspace_path: str,
    requester: str,
) -> str:
    payload = {
        "code": code,
        "plan_json": normalize_plan_json(plan_json),
        "workspace_path": workspace_path,
        "requester": requester.strip().lower(),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()
