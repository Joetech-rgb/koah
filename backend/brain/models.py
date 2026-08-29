from __future__ import annotations

from django.db import models


class TimeStampedModel(models.Model):
    """Abstract base providing created/updated timestamps for auditability."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class CompanyProfile(TimeStampedModel):
    """The single source of truth for KoahCloud's identity and positioning.

    In practice this table should hold exactly one row; the agent pipeline
    reads from it to build system prompts for research and drafting.
    """

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    email_tone = models.CharField(
        max_length=255,
        blank=True,
        help_text="e.g. friendly, formal, direct",
    )
    based_in = models.CharField(max_length=255, default="Ghana")

    class Meta:
        verbose_name = "Company Profile"
        verbose_name_plural = "Company Profiles"

    def __str__(self) -> str:
        return self.name


class Service(TimeStampedModel):
    """A service KoahCloud offers, tagged with the prospect signal it targets."""

    company = models.ForeignKey(
        CompanyProfile, on_delete=models.CASCADE, related_name="services"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    target_signal = models.CharField(
        max_length=255,
        blank=True,
        help_text="Prospect signal that suggests this service fits, "
                   "e.g. 'no website detected'",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Product(TimeStampedModel):
    """A physical or bundled product (e.g. laptops, IT equipment)."""

    company = models.ForeignKey(
        CompanyProfile, on_delete=models.CASCADE, related_name="products"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="products/", blank=True, null=True)
    price_note = models.CharField(
        max_length=255, blank=True, help_text="e.g. 'from $500'"
    )

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class PortfolioItem(TimeStampedModel):
    """Past work used as social proof in drafted pitches."""

    company = models.ForeignKey(
        CompanyProfile, on_delete=models.CASCADE, related_name="portfolio_items"
    )
    title = models.CharField(max_length=255)
    summary = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title


class SalesRule(TimeStampedModel):
    """A standing instruction the drafting agent must always follow.

    e.g. "Always mention laptops as an add-on",
         "Introduce as Ghana-based for international leads".
    """

    company = models.ForeignKey(
        CompanyProfile, on_delete=models.CASCADE, related_name="sales_rules"
    )
    rule_text = models.TextField()

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return self.rule_text[:60]


class ProposalTemplate(TimeStampedModel):
    """A reusable proposal/pitch skeleton the agent can adapt."""

    company = models.ForeignKey(
        CompanyProfile, on_delete=models.CASCADE, related_name="proposal_templates"
    )
    name = models.CharField(max_length=255)
    template_text = models.TextField()

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name