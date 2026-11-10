from django.conf import settings
from django.db import models


class NicheConfig(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="niche_configs")
    niche_name = models.CharField(max_length=100)
    region = models.CharField(max_length=100)
    active = models.BooleanField(default=True)
    sources = models.JSONField(default=list, blank=True)
    playbook = models.TextField(blank=True)
    last_searched_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("owner", "niche_name", "region")

    def __str__(self):
        return f"{self.niche_name} - {self.region}"
