from rest_framework import serializers
from .models import DailyDigest


class DailyDigestSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyDigest
        fields = ["id", "date", "businesses_found", "emails_sent", "replies_received", "hot_leads"]
