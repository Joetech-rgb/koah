from django.db import models


class PromptTemplate(models.Model):
    key = models.CharField(max_length=100)
    version = models.CharField(max_length=20, default="1.0")
    template = models.TextField()
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("key", "version")

    def __str__(self):
        return f"{self.key} v{self.version}"


class AgentInvocation(models.Model):
    prompt_key = models.CharField(max_length=100)
    input_payload = models.JSONField()
    output_payload = models.JSONField()
    model_used = models.CharField(max_length=100)
    tokens_in = models.IntegerField(default=0)
    tokens_out = models.IntegerField(default=0)
    cost_usd = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[('success', 'Success'), ('failed', 'Failed')], default='success')
    duration_ms = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.prompt_key} @ {self.created_at:%Y-%m-%d %H:%M}"
