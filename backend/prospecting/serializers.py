from rest_framework import serializers
from .models import NicheConfig


class NicheConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = NicheConfig
        fields = ["id", "niche_name", "region", "active"]
