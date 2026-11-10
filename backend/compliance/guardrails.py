import redis
from decouple import config as env_config
from django.utils import timezone

from .models import SuppressedContact

_redis_client = redis.from_url(env_config("REDIS_URL", default="redis://localhost:6379/0"))

SEND_RATE_LIMIT_PER_HOUR = env_config("SEND_RATE_LIMIT_PER_HOUR", default=30, cast=int)


def is_suppressed(email: str) -> bool:
    if not email:
        return True
    return SuppressedContact.objects.filter(email=email).exists()


def inject_unsubscribe_and_sender_id(body: str, company) -> str:
    footer = (
        f"\n\n---\n"
        f"{company.name}"
        f"{(' - ' + company.based_in) if getattr(company, 'based_in', None) else ''}\n"
        f"If you'd rather not hear from us again, just reply with 'unsubscribe'."
    )
    return body + footer


def check_send_rate_limit(mailbox_id: str) -> bool:
    hour_key = f"send_count:{mailbox_id}:{timezone.now().strftime('%Y%m%d%H')}"
    current_count = _redis_client.incr(hour_key)
    if current_count == 1:
        _redis_client.expire(hour_key, 3600)
    return current_count <= SEND_RATE_LIMIT_PER_HOUR
