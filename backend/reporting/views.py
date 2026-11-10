from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta

from .models import DailyDigest
from .serializers import DailyDigestSerializer
from agent.models import AgentInvocation
from outreach.models import EmailMessage, EmailThread


class DailyDigestViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DailyDigest.objects.all().order_by("-date")
    serializer_class = DailyDigestSerializer
    lookup_field = "date"
    permission_classes = []
    authentication_classes = []

    @action(detail=False, methods=["get"])
    def stats(self, request):
        today = timezone.now().date()
        month_start = today.replace(day=1)
        week_ago = today - timedelta(days=7)
        two_weeks_ago = today - timedelta(days=14)

        cost_this_month = AgentInvocation.objects.filter(
            created_at__date__gte=month_start
        ).aggregate(total=Sum("cost_usd"))["total"] or 0

        sent_this_week = EmailMessage.objects.filter(
            direction="outbound", sent_at__date__gte=week_ago
        ).count()
        sent_last_week = EmailMessage.objects.filter(
            direction="outbound", sent_at__date__gte=two_weeks_ago, sent_at__date__lt=week_ago
        ).count()

        total_sent_7d = EmailMessage.objects.filter(
            direction="outbound", sent_at__date__gte=week_ago
        ).count()
        total_replies_7d = EmailThread.objects.filter(
            status__in=["replied", "closed"], created_at__date__gte=week_ago
        ).count()
        reply_rate = (total_replies_7d / total_sent_7d) if total_sent_7d else 0

        return Response({
            "cost_this_month": float(cost_this_month),
            "emails_sent_this_week": sent_this_week,
            "emails_sent_last_week": sent_last_week,
            "reply_rate_7d": round(reply_rate, 3),
        })
