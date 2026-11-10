from __future__ import annotations
from django.conf import settings
from django.db import models


class CandidateProfile(models.Model):
    REMOTE_CHOICES = [
        ("remote_only", "Remote only"),
        ("remote_preferred", "Remote preferred"),
        ("open", "Open to remote or onsite"),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="candidate_profile")
    summary = models.TextField(blank=True, help_text="A short professional summary, used as context for AI-drafted applications.")
    years_experience = models.PositiveIntegerField(default=0)
    preferred_roles = models.CharField(max_length=500, blank=True, help_text="Comma-separated, e.g. 'Backend Developer, Python Developer'")
    preferred_regions = models.CharField(max_length=500, blank=True, help_text="Comma-separated, e.g. 'Remote - Worldwide, Remote - Europe'")
    remote_preference = models.CharField(max_length=20, choices=REMOTE_CHOICES, default="remote_preferred")
    cv_file = models.FileField(upload_to="cvs/", blank=True, null=True, help_text="Optional - for reference/attachment, not read by the AI directly.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Candidate profile for {self.user.username}"


class Skill(models.Model):
    PROFICIENCY_CHOICES = [
        ("beginner", "Beginner"),
        ("intermediate", "Intermediate"),
        ("advanced", "Advanced"),
        ("expert", "Expert"),
    ]

    profile = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name="skills")
    name = models.CharField(max_length=100)
    proficiency = models.CharField(max_length=20, choices=PROFICIENCY_CHOICES, default="intermediate")
    years = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Experience(models.Model):
    profile = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name="experiences")
    company = models.CharField(max_length=255)
    role = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True, help_text="Leave blank if this is your current role.")
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.role} at {self.company}"


class JobSearchConfig(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="job_search_configs")
    role_query = models.CharField(max_length=255, help_text="e.g. 'backend developer'")
    region = models.CharField(max_length=255, help_text="e.g. 'remote worldwide', 'remote Europe'")
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    CATEGORY_CHOICES = [
        ("general", "General"),
        ("ai_training", "AI Training (micro1-style)"),
        ("startup", "Startup / Entry-Level"),
        ("internship", "Internship"),
        ("visa_sponsorship", "Visa Sponsorship"),
        ("gig_platforms", "Gig & Microtask Platforms"),
        ("ngo", "NGO / International Development"),
    ]
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default="general")

    def __str__(self):
        return f"{self.role_query} - {self.region}"


class JobListing(models.Model):
    STATUS_CHOICES = [
        ("found", "Found"),
        ("has_email", "Has Direct Email"),
        ("apply_manually", "Apply Manually"),
        ("applied", "Applied"),
        ("replied", "Replied"),
        ("interview", "Interview"),
        ("rejected", "Rejected"),
        ("closed", "Closed"),
    ]

    config = models.ForeignKey(JobSearchConfig, on_delete=models.CASCADE, related_name="listings")
    title = models.CharField(max_length=255)
    company_name = models.CharField(max_length=255, blank=True)
    source_url = models.URLField(max_length=800)
    snippet = models.TextField(blank=True)
    application_email = models.EmailField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="found")
    ai_talking_points = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["config", "source_url"], name="uniq_config_source_url"),
        ]

    def __str__(self):
        return self.title
