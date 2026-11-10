from django.db import models
from django.conf import settings


class TargetCompany(models.Model):
    STATUS_CHOICES = [
        ("new", "New"),
        ("researched", "Researched"),
        ("drafted", "Drafted"),
        ("sent", "Sent"),
        ("replied", "Replied"),
        ("closed", "Closed"),
        ("rejected", "Rejected"),
    ]

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="target_companies")
    name = models.CharField(max_length=255)
    domain = models.CharField(max_length=255, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    industry = models.CharField(max_length=100, blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    contact_phone = models.CharField(max_length=30, blank=True, null=True)

    WEBSITE_STATUS_CHOICES = [
        ("unknown", "Unknown"),
        ("none", "No website"),
        ("social_only", "Social/Google listing only"),
        ("has_website", "Has website"),
    ]

    contact_address = models.CharField(max_length=300, blank=True, null=True)
    google_cid = models.CharField(max_length=64, blank=True, null=True)
    facebook_url = models.URLField(max_length=300, blank=True, null=True)
    social_url = models.URLField(max_length=300, blank=True, null=True)
    social_platform = models.CharField(max_length=20, blank=True, null=True)
    org_type = models.CharField(max_length=100, blank=True, null=True)
    website_status = models.CharField(max_length=20, choices=WEBSITE_STATUS_CHOICES, default="unknown")
    discovery_source = models.CharField(max_length=20, blank=True, null=True)
    pitch_angles = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="new")
    source_niche = models.ForeignKey("prospecting.NicheConfig", on_delete=models.SET_NULL, null=True, blank=True, related_name="companies_found")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["owner", "google_cid"], name="uniq_owner_google_cid"),
        ]


class ResearchResult(models.Model):
    target_company = models.OneToOneField(TargetCompany, on_delete=models.CASCADE, related_name="research_result")
    has_website = models.BooleanField(default=False)
    detected_industry = models.CharField(max_length=100, blank=True)
    detected_tools = models.JSONField(default=list)
    summary = models.TextField(blank=True)

    def __str__(self):
        return f"Research for {self.target_company.name}"
