from celery import shared_task
from django.utils import timezone
from django.db.models import Q

from crm.models import TargetCompany
from outreach.models import EmailThread, EmailMessage
from .models import DailyDigest


@shared_task
def generate_daily_digest_task():
    today = timezone.now().date()

    businesses_found = TargetCompany.objects.filter(created_at__date=today).count()
    emails_sent = EmailMessage.objects.filter(
        direction="outbound", sent_at__date=today
    ).count()
    replies_received = EmailMessage.objects.filter(
        direction="inbound", created_at__date=today
    ).count()

    hot_threads = EmailThread.objects.filter(
        status="replied", classification="interested"
    )
    hot_leads = [
        {"name": t.target_company.name, "thread_id": t.id, "reason": "classified as interested"}
        for t in hot_threads
    ]

    digest, _ = DailyDigest.objects.update_or_create(
        date=today,
        defaults={
            "businesses_found": businesses_found,
            "emails_sent": emails_sent,
            "replies_received": replies_received,
            "hot_leads": hot_leads,
        },
    )

    from decouple import config as env_config
    recipient = env_config("REPORT_RECIPIENT_EMAIL", default="")
    if recipient:
        try:
            from mailbox_app.services.gmail_client import send_email
            body = (
                f"Daily Digest for {today}\n\n"
                f"Businesses found: {businesses_found}\n"
                f"Emails sent: {emails_sent}\n"
                f"Replies received: {replies_received}\n"
                f"Hot leads: {len(hot_leads)}\n"
            )
            send_email(recipient, f"KoahCloud Daily Digest - {today}", body)
        except Exception:
            pass

    return digest.id
