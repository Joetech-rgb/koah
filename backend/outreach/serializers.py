from rest_framework import serializers
from .models import EmailMessage


class EmailMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailMessage
        fields = ["id", "thread", "direction", "body", "sent_at", "provider_message_id", "created_at"]
