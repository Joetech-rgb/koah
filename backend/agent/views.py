from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as http_status

from crm.models import TargetCompany, ResearchResult
from brain.models import CompanyProfile, Service, Product, SalesRule
from .serializers import ResearchAndDraftRequestSerializer
from .services.interfaces import ResearchInput, DraftInput
from .services.research import research_company
from .services.drafting import draft_pitch


def _build_brain_context() -> dict:
    company = CompanyProfile.objects.first()
    if not company:
        return {}
    return {
        "company": {
            "name": company.name,
            "description": company.description,
            "email_tone": company.email_tone,
        },
        "services": list(Service.objects.filter(company_profile=company).values("name", "description")),
        "products": list(Product.objects.filter(company_profile=company).values("name", "description")),
        "sales_rules": list(SalesRule.objects.filter(company_profile=company).values_list("rule_text", flat=True)),
    }


@method_decorator(csrf_exempt, name="dispatch")
class ResearchAndDraftView(APIView):
    permission_classes = []
    authentication_classes = []
    def post(self, request):
        serializer = ResearchAndDraftRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        target_company, _ = TargetCompany.objects.get_or_create(
            name=data["company_name"],
            defaults={"domain": data.get("domain", ""), "country": data.get("country", "")},
        )

        research_input = ResearchInput(
            company_name=data["company_name"],
            domain=data.get("domain"),
            country=data.get("country"),
        )
        research_output = research_company(research_input)

        ResearchResult.objects.update_or_create(
            target_company=target_company,
            defaults={
                "has_website": research_output.has_website,
                "detected_industry": research_output.detected_industry,
                "detected_tools": research_output.detected_tools,
                "summary": research_output.summary,
            },
        )
        target_company.industry = research_output.detected_industry
        target_company.status = "researched"
        target_company.save()

        brain_context = _build_brain_context()
        brain_context["country"] = data.get("country")

        draft_input = DraftInput(research=research_output, brain_context=brain_context)
        draft_output = draft_pitch(draft_input)

        target_company.status = "drafted"
        target_company.save()

        return Response(
            {
                "detected_industry": research_output.detected_industry,
                "has_website": research_output.has_website,
                "pitch_angle": draft_output.pitch_angle,
                "subject": draft_output.subject,
                "body": draft_output.body,
            },
            status=http_status.HTTP_200_OK,
        )
