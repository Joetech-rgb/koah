from compliance.models import AuditLog

VALID_TRANSITIONS = {
    "drafted": ["guardrail_checked"],
    "guardrail_checked": ["sent"],
    "sent": ["awaiting_reply"],
    "awaiting_reply": ["replied"],
    "replied": ["closed"],
}


class InvalidTransitionError(Exception):
    pass


def transition(thread, new_status: str):
    current_status = thread.status
    allowed = VALID_TRANSITIONS.get(current_status, [])
    if new_status not in allowed:
        raise InvalidTransitionError(
            f"Cannot transition thread {thread.id} from '{current_status}' to '{new_status}'"
        )

    old_status = thread.status
    thread.status = new_status
    thread.save()

    AuditLog.objects.create(
        action="status_transition",
        target_type="EmailThread",
        target_id=thread.id,
        detail={"from": old_status, "to": new_status},
    )
    return thread
