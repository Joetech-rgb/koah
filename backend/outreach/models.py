from django.db import models
from crm.models import TargetCompany


class EmailThread(models.Model):
    STATUS_CHOICES = [
        ("drafted", "Drafted"),
        ("guardrail_checked", "Guardrail Checked"),
        ("sent", "Sent"),
        ("awaiting_reply", "Awaiting Reply"),
        ("replied", "Replied"),
        ("closed", "Closed"),
    ]

    target_company = models.ForeignKey(TargetCompany, on_delete=models.CASCADE, related_name="threads")
    subject = models.CharField(max_length=255)
    pitch_angle = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="drafted")
    classification = models.CharField(max_length=30, blank=True, null=True)
    provider_thread_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.target_company.name} - {self.subject}"


class EmailMessage(models.Model):
    DIRECTION_CHOICES = [
        ("outbound", "Outbound"),
        ("inbound", "Inbound"),
    ]

    thread = models.ForeignKey(EmailThread, on_delete=models.CASCADE, related_name="messages")
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    body = models.TextField()
    sent_at = models.DateTimeField(null=True, blank=True)
    provider_message_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.direction} message on thread {self.thread_id}"
