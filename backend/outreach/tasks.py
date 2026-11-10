from celery import shared_task

from .models import EmailThread, EmailMessage
from .state_machine import transition
from compliance.models import SuppressedContact

OPT_OUT_PHRASES = [
    "unsubscribe", "stop emailing", "stop sending", "stop contacting", "remove me",
    "take me off", "do not contact", "don't contact", "dont contact", "opt out", "opt-out",
]


def _fresh_text(body):
    out = []
    for line in (body or "").splitlines():
        s = line.strip()
        if s.startswith(">") or (s.startswith("On ") and "wrote" in s):
            break
        out.append(line)
    return "\n".join(out).lower()



@shared_task
def classify_and_reply_task(thread_id):
    from agent.services.reply_handling import classify_reply, draft_reply
    from mailbox_app.tasks import send_email_task

    thread = EmailThread.objects.get(id=thread_id)
    last_in = thread.messages.filter(direction='inbound').order_by('-created_at').first()
    if last_in and any(p in _fresh_text(last_in.body) for p in OPT_OUT_PHRASES):
        contact_email = thread.target_company.contact_email
        if contact_email:
            SuppressedContact.objects.get_or_create(email=contact_email, defaults={'reason': 'opt-out phrase in reply'})
        transition(thread, 'closed')
        return 'closed_opt_out'
    classification = classify_reply(thread)

    if classification == "not_interested":
        contact_email = thread.target_company.contact_email
        if contact_email:
            SuppressedContact.objects.get_or_create(
                email=contact_email,
                defaults={"reason": "classified not_interested"},
            )
        transition(thread, "closed")
        return "closed"

    if classification == 'out_of_office':
        return 'out_of_office'

    draft_output = draft_reply(thread)
    EmailMessage.objects.create(
        thread=thread,
        direction="outbound",
        body=draft_output.body,
    )
    from django.conf import settings
    if getattr(settings, "AUTO_REPLY_ENABLED", False):
        send_email_task.delay(thread.id)
        return "replying"
    return "reply_drafted_for_review"
