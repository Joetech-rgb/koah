from celery import shared_task
from django.core.cache import cache
from decouple import config as env_config


@shared_task
def check_mailbox_health_task():
    try:
        from mailbox_app.services.gmail_client import _get_service
        service = _get_service()
        service.users().getProfile(userId="me").execute()
        cache.delete("SENDING_PAUSED")
        return "healthy"
    except Exception as e:
        cache.set("SENDING_PAUSED", True, timeout=None)

        recipient = env_config("REPORT_RECIPIENT_EMAIL", default="")
        if recipient:
            try:
                from mailbox_app.services.gmail_client import send_email
                send_email(
                    recipient,
                    "KoahCloud ALERT: Mailbox needs re-authorization",
                    f"The Gmail mailbox connection failed with error:\n\n{str(e)}\n\n"
                    f"Sending has been paused. Please re-run the OAuth flow to restore it.",
                )
            except Exception:
                pass
        return f"unhealthy: {e}"
