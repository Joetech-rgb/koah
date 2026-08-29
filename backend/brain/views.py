from __future__ import annotations

from rest_framework import viewsets
from rest_framework.permissions import AllowAny

from .models import CompanyProfile, Product, Service
from .serializers import CompanyProfileSerializer, ProductSerializer, ServiceSerializer

# NOTE: AllowAny is temporary for local frontend development.
# Switch back to IsAuthenticated (or a proper token/session auth flow)
# before any real deployment.


class CompanyProfileViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only access to KoahCloud's company profile(s)."""

    queryset = CompanyProfile.objects.all()
    serializer_class = CompanyProfileSerializer
    permission_classes = [AllowAny]


class ServiceViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only access to the services catalogue."""

    queryset = Service.objects.select_related("company").all()
    serializer_class = ServiceSerializer
    permission_classes = [AllowAny]


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only access to the product catalogue."""

    queryset = Product.objects.select_related("company").all()
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]