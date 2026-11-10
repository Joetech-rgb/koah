from celery import shared_task

from .models import JobSearchConfig, JobListing
from .services.discovery import find_jobs, extract_email_from_url
from concurrent.futures import ThreadPoolExecutor

_POOL = ThreadPoolExecutor(max_workers=8)


def _email_safe(url, timeout=12):
    f = _POOL.submit(extract_email_from_url, url)
    try:
        return f.result(timeout=timeout)
    except Exception:
        return None


@shared_task
def discover_jobs_task(user_id=None):
    created_ids = []
    for config in JobSearchConfig.objects.filter(active=True, **({"user_id": user_id} if user_id else {})):
        try:
            results = find_jobs(config.role_query, config.region)
        except Exception:
            continue

        for item in results:
            source_url = item.get("source_url", "")
            if not source_url or JobListing.objects.filter(config__user=config.user, source_url=source_url).exists():
                continue

            email = _email_safe(source_url)
            listing = JobListing.objects.create(
                config=config,
                title=item.get("title", ""),
                company_name=item.get("company_name", ""),
                source_url=source_url,
                snippet=item.get("snippet", ""),
                application_email=email,
                status="has_email" if email else "apply_manually",
            )
            created_ids.append(listing.id)
    return created_ids
