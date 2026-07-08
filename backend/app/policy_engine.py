import re
from pathlib import Path

import yaml

from app.models import PolicyFinding

POLICIES_DIR = Path(__file__).resolve().parent.parent / "policies"


def _load_rules() -> list[dict]:
    rules: list[dict] = []
    for policy_file in sorted(POLICIES_DIR.glob("*.yaml")):
        with policy_file.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        for rule in data.get("policies", []):
            if rule.get("pattern"):
                rules.append(rule)

    return rules


def _check_missing_encryption(code: str) -> list[PolicyFinding]:
    """Flag S3 buckets that have no server_side_encryption_configuration block."""
    findings: list[PolicyFinding] = []
    if "aws_s3_bucket" not in code:
        return findings
    if "server_side_encryption_configuration" in code:
        return findings

    for i, line in enumerate(code.splitlines(), start=1):
        if re.search(r'resource\s+"aws_s3_bucket"', line):
            findings.append(
                PolicyFinding(
                    policy_id="ENC-003",
                    term="missing encryption",
                    line_number=i,
                    severity="medium",
                    category="encryption",
                    message="S3 bucket defined without server-side encryption configuration",
                    remediation="Add a server_side_encryption_configuration block with AES256 or KMS",
                    source="rule_engine",
                    matched_text=line.strip(),
                )
            )
            break
    return findings


def scan_with_rules(code: str) -> list[PolicyFinding]:
    """Evaluate all declarative policy rules against Terraform HCL."""
    findings: list[PolicyFinding] = []
    seen: set[tuple[str, int]] = set()
    lines = code.splitlines()
    rules = _load_rules()

    for line_num, line in enumerate(lines, start=1):
        for rule in rules:
            if not re.search(rule["pattern"], line):
                continue
            key = (rule["id"], line_num)
            if key in seen:
                continue
            seen.add(key)
            findings.append(
                PolicyFinding(
                    policy_id=rule["id"],
                    term=rule["name"],
                    line_number=line_num,
                    severity=rule["severity"],
                    category=rule["category"],
                    message=rule["message"],
                    remediation=rule["remediation"],
                    source="rule_engine",
                    matched_text=line.strip(),
                )
            )

    findings.extend(_check_missing_encryption(code))
    return findings
