from rest_framework import viewsets
from .models import TargetCompany
from .serializers import TargetCompanySerializer


class TargetCompanyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TargetCompany.objects.all().order_by("-created_at")
    serializer_class = TargetCompanySerializer
    permission_classes = []
    authentication_classes = []
