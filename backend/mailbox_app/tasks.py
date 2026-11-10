from celery import shared_task
from django.core.cache import cache

from outreach.models import EmailThread, EmailMessage
from outreach.state_machine import transition
from compliance.guardrails import is_suppressed, inject_unsubscribe_and_sender_id, check_send_rate_limit
from compliance.models import SuppressedContact, AuditLog
from brain.models import CompanyProfile
from .services.gmail_client import send_email, fetch_new_replies, get_thread_id, mark_as_read


@shared_task(bind=True, max_retries=5, default_retry_delay=300)
def send_email_task(self, thread_id):
    if cache.get("SENDING_PAUSED"):
        raise self.retry(countdown=600)

    thread = EmailThread.objects.get(id=thread_id)
    draft_message = thread.messages.filter(direction="outbound", sent_at__isnull=True).order_by("-created_at").first()
    if not draft_message:
        return None

    to_email = thread.target_company.contact_email
    if not to_email:
        return None  # no email on file (phone/Facebook-only prospect)
    if is_suppressed(to_email):
        SuppressedContact.objects.get_or_create(email=to_email, defaults={"reason": "already suppressed"})
        return None

    if not check_send_rate_limit("primary_mailbox"):
        raise self.retry(countdown=900)

    company = CompanyProfile.objects.first()
    final_body = inject_unsubscribe_and_sender_id(draft_message.body, company) if company else draft_message.body

    message_id = send_email(to_email, thread.subject, final_body)

    from django.utils import timezone
    draft_message.sent_at = timezone.now()
    draft_message.provider_message_id = message_id
    draft_message.body = final_body
    draft_message.save()

    provider_thread_id = get_thread_id(message_id)
    thread.provider_thread_id = provider_thread_id
    thread.save(update_fields=["provider_thread_id"])

    transition(thread, "guardrail_checked")
    transition(thread, "sent")
    transition(thread, "awaiting_reply")
    return message_id


@shared_task
def poll_replies_task():
    from outreach.tasks import classify_and_reply_task

    replies = fetch_new_replies()
    handled = []
    for reply in replies:
        thread = EmailThread.objects.filter(provider_thread_id=reply["thread_id"]).first()

        if not thread:
            AuditLog.objects.create(
                action="skip_unmatched_reply",
                target_type="gmail_message",
                target_id=reply["message_id"],
                detail={"from_email": reply["from_email"], "reason": "no matching EmailThread"},
            )
            mark_as_read(reply["message_id"])
            continue

        if thread.messages.filter(provider_message_id=reply["message_id"]).exists():
            mark_as_read(reply["message_id"])
            continue

        EmailMessage.objects.create(
            thread=thread,
            direction="inbound",
            body=reply["body"],
            provider_message_id=reply["message_id"],
        )
        transition(thread, "replied")
        classify_and_reply_task.delay(thread.id)
        mark_as_read(reply["message_id"])
        handled.append(thread.id)
    return handled
