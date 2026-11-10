from rest_framework import serializers


class ResearchAndDraftRequestSerializer(serializers.Serializer):
    company_name = serializers.CharField()
    domain = serializers.CharField(required=False, allow_blank=True)
    country = serializers.CharField(required=False, allow_blank=True)
