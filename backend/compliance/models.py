from django.db import models


class SuppressedContact(models.Model):
    email = models.EmailField(unique=True)
    reason = models.CharField(max_length=255)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email


class AuditLog(models.Model):
    action = models.CharField(max_length=100)
    target_type = models.CharField(max_length=100)
    target_id = models.IntegerField()
    detail = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action} on {self.target_type}#{self.target_id}"
