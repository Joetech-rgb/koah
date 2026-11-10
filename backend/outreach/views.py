from rest_framework import viewsets
from .models import EmailMessage
from .serializers import EmailMessageSerializer


class EmailMessageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = EmailMessage.objects.all().order_by("-created_at")
    serializer_class = EmailMessageSerializer
    permission_classes = []
    authentication_classes = []

    def get_queryset(self):
        qs = super().get_queryset()
        date = self.request.query_params.get("date")
        if date:
            qs = qs.filter(created_at__date=date)
        return qs
