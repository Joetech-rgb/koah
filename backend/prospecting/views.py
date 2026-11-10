from rest_framework import viewsets
from .models import NicheConfig
from .serializers import NicheConfigSerializer


class NicheConfigViewSet(viewsets.ModelViewSet):
    queryset = NicheConfig.objects.all().order_by("niche_name")
    serializer_class = NicheConfigSerializer
    permission_classes = []
    authentication_classes = []
