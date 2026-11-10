from rest_framework import serializers
from .models import TargetCompany


class TargetCompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = TargetCompany
        fields = ["id", "name", "domain", "country", "industry", "status", "contact_email", "created_at"]
