from django.db import models


class DailyDigest(models.Model):
    date = models.DateField(unique=True)
    businesses_found = models.IntegerField(default=0)
    emails_sent = models.IntegerField(default=0)
    replies_received = models.IntegerField(default=0)
    hot_leads = models.JSONField(default=list)

    def __str__(self):
        return f"Digest for {self.date}"
