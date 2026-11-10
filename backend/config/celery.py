import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')

app = Celery('config')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "start-daily-discovery": {
        "task": "prospecting.tasks.discover_companies_task",
        "schedule": crontab(hour=8, minute=0),
    },
    "start-daily-job-discovery": {
        "task": "jobs.tasks.discover_jobs_task",
        "schedule": crontab(hour=8, minute=30),
    },
    "poll-replies": {
        "task": "mailbox_app.tasks.poll_replies_task",
        "schedule": crontab(minute="*/15", hour="8-17"),
    },
    "generate-daily-report": {
        "task": "reporting.tasks.generate_daily_digest_task",
        "schedule": crontab(hour=17, minute=0),
    },
    "check-mailbox-health": {
        "task": "compliance.tasks.check_mailbox_health_task",
        "schedule": crontab(minute=0, hour="8-17"),
    },
}
