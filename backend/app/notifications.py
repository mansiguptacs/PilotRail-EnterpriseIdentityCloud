from app.models import Plan
from app.store import save_notification

APPROVER_CHANNEL = "#security-approvals"
APPROVER_RECIPIENT = "@security-team"


def notify_approver(plan: Plan) -> None:
    message = (
        f"New {plan.risk_tier} risk access change from {plan.requester} "
        f"— review required (plan {plan.id[:8]}...)"
    )
    save_notification(
        plan_id=plan.id,
        recipient=APPROVER_RECIPIENT,
        channel=APPROVER_CHANNEL,
        message=message,
        event_type="NOTIFY_APPROVER",
    )


def notify_requester_approved(plan: Plan, reviewer: str) -> None:
    message = (
        f"Your change was approved by {reviewer}. "
        f"Re-run `terraform apply` to proceed (plan {plan.id[:8]}...)."
    )
    save_notification(
        plan_id=plan.id,
        recipient=plan.requester,
        channel=f"@{plan.requester}",
        message=message,
        event_type="NOTIFY_REQUESTER",
    )


def notify_requester_rejected(plan: Plan, reviewer: str, reason: str) -> None:
    message = (
        f"Your change was rejected by {reviewer}: {reason}. "
        f"Revise the Terraform and submit again."
    )
    save_notification(
        plan_id=plan.id,
        recipient=plan.requester,
        channel=f"@{plan.requester}",
        message=message,
        event_type="NOTIFY_REQUESTER",
    )
