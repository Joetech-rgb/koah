from __future__ import annotations

from rest_framework import serializers

from .models import CompanyProfile, Product, Service


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ("id", "name", "description", "target_signal")
        read_only_fields = fields


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ("id", "name", "description", "image", "price_note")
        read_only_fields = fields


class CompanyProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyProfile
        fields = ("id", "name", "description", "email_tone", "based_in")
        read_only_fields = fields