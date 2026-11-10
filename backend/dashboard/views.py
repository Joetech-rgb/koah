from datetime import timedelta

from django.conf import settings as django_settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from crm.models import TargetCompany, ResearchResult
from outreach.models import EmailThread, EmailMessage
from brain.models import CompanyProfile, Service, Product, PortfolioItem, SalesRule, ProposalTemplate
from agent.models import AgentInvocation, PromptTemplate
from compliance.models import SuppressedContact, AuditLog
from prospecting.models import NicheConfig
from reporting.models import DailyDigest


from functools import wraps


def _co(request):
    return TargetCompany.objects.filter(owner=request.user)


def _threads(request):
    return EmailThread.objects.filter(target_company__owner=request.user)


def _msgs(request):
    return EmailMessage.objects.filter(thread__target_company__owner=request.user)


def _niches(request):
    return NicheConfig.objects.filter(owner=request.user)


def _staff_only(view):
    @wraps(view)
    def inner(request, *args, **kwargs):
        if not request.user.is_superuser:
            messages.error(request, "That page is only available to the platform administrator.")
            return redirect("dashboard")
        return view(request, *args, **kwargs)
    return inner


def _celery_is_running():
    try:
        from config.celery import app as celery_app
        pong = celery_app.control.inspect(timeout=1).ping()
        return bool(pong)
    except Exception:
        return False


def _pct_change(curr, prev):
    if prev == 0:
        return 100 if curr > 0 else 0
    return round(((curr - prev) / prev) * 100)


def _default_company(request):
    company = CompanyProfile.objects.filter(owner=request.user).first()
    if not company:
        company = CompanyProfile.objects.create(owner=request.user, name=request.user.get_username(), based_in="Ghana")
    return company


def dashboard(request):
    today = timezone.localdate()
    days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    start, end = days[0], today
    prev_start, prev_end = start - timedelta(days=7), start - timedelta(days=1)

    businesses_found = _co(request).filter(created_at__date__gte=start, created_at__date__lte=end).count()
    businesses_found_prev = _co(request).filter(created_at__date__gte=prev_start, created_at__date__lte=prev_end).count()

    emails_sent = _msgs(request).filter(direction="outbound", sent_at__date__gte=start, sent_at__date__lte=end).count()
    emails_sent_prev = _msgs(request).filter(direction="outbound", sent_at__date__gte=prev_start, sent_at__date__lte=prev_end).count()

    replies_received = _msgs(request).filter(direction="inbound", created_at__date__gte=start, created_at__date__lte=end).count()
    replies_received_prev = _msgs(request).filter(direction="inbound", created_at__date__gte=prev_start, created_at__date__lte=prev_end).count()

    interested_leads = _threads(request).filter(classification="interested", created_at__date__gte=start, created_at__date__lte=end).count()
    interested_leads_prev = _threads(request).filter(classification="interested", created_at__date__gte=prev_start, created_at__date__lte=prev_end).count()

    chart_labels = [f"{d.strftime('%b')} {d.day}" for d in days]
    emails_series = [_msgs(request).filter(direction="outbound", sent_at__date=d).count() for d in days]
    replies_series = [_msgs(request).filter(direction="inbound", created_at__date=d).count() for d in days]
    interested_series = [_threads(request).filter(classification="interested", created_at__date=d).count() for d in days]

    last_company = _co(request).order_by("-created_at").first()

    recent_activity = []
    for m in _msgs(request).filter(direction="outbound", sent_at__isnull=False).order_by("-sent_at")[:5]:
        recent_activity.append({"type": "Email sent", "details": f"{m.thread.target_company.name} - {m.thread.subject}", "time": m.sent_at, "status": "Sent", "badge": "info"})
    for m in _msgs(request).filter(direction="inbound").order_by("-created_at")[:5]:
        recent_activity.append({"type": "Reply received", "details": f"{m.thread.target_company.name}", "time": m.created_at, "status": "Replied", "badge": "success"})
    for c in _co(request).order_by("-created_at")[:5]:
        recent_activity.append({"type": "New company found", "details": c.name, "time": c.created_at, "status": "New", "badge": "warning"})
    recent_activity.sort(key=lambda x: x["time"], reverse=True)
    recent_activity = recent_activity[:8]

    recent_companies = _co(request).order_by("-created_at")[:6]
    recent_threads = _threads(request).select_related("target_company").order_by("-created_at")[:6]

    context = {
        "kpis": {
            "businesses_found": businesses_found,
            "businesses_found_change": _pct_change(businesses_found, businesses_found_prev),
            "emails_sent": emails_sent,
            "emails_sent_change": _pct_change(emails_sent, emails_sent_prev),
            "replies_received": replies_received,
            "replies_received_change": _pct_change(replies_received, replies_received_prev),
            "interested_leads": interested_leads,
            "interested_leads_change": _pct_change(interested_leads, interested_leads_prev),
        },
        "chart_labels": chart_labels,
        "emails_series": emails_series,
        "replies_series": replies_series,
        "interested_series": interested_series,
        "agent_running": _celery_is_running(),
        "last_company": last_company,
        "recent_activity": recent_activity,
        "recent_companies": recent_companies,
        "recent_threads": recent_threads,
    }
    return render(request, "dashboard/index.html", context)


def companies_list(request):
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    country = request.GET.get("country", "")
    industry = request.GET.get("industry", "")

    qs = _co(request).all().order_by("-created_at")
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(domain__icontains=q) | Q(contact_email__icontains=q))
    if status:
        qs = qs.filter(status=status)
    if country:
        qs = qs.filter(country=country)
    if industry:
        qs = qs.filter(industry=industry)

    total = _co(request).count()
    researching = _co(request).filter(status="researched").count()
    contacted = _co(request).filter(status__in=["sent", "replied", "closed"]).count()
    replied = _co(request).filter(status="replied").count()
    interested = _co(request).filter(threads__classification="interested").distinct().count()

    countries = _co(request).exclude(country__isnull=True).exclude(country="").values_list("country", flat=True).distinct().order_by("country")
    industries = _co(request).exclude(industry__isnull=True).exclude(industry="").values_list("industry", flat=True).distinct().order_by("industry")

    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "page_obj": page_obj,
        "total": total, "researching": researching, "contacted": contacted,
        "replied": replied, "interested": interested,
        "countries": countries, "industries": industries,
        "q": q, "status": status, "country": country, "industry": industry,
        "status_choices": TargetCompany.STATUS_CHOICES,
    }
    return render(request, "dashboard/companies.html", context)


def company_detail(request, pk):
    company = get_object_or_404(_co(request), pk=pk)
    research = getattr(company, "research_result", None)
    threads = _threads(request).filter(target_company=company).order_by("-created_at")
    context = {"company": company, "research": research, "threads": threads}
    return render(request, "dashboard/company_detail.html", context)


def company_add(request):
    if request.method == "POST":
        TargetCompany.objects.create(
            owner=request.user,
            name=request.POST.get("name", "").strip(),
            domain=request.POST.get("domain", "").strip(),
            country=request.POST.get("country", "").strip(),
            industry=request.POST.get("industry", "").strip(),
            contact_email=request.POST.get("contact_email", "").strip(),
        )
        messages.success(request, "Company added.")
        return redirect("companies")
    return render(request, "dashboard/company_add.html")


def outreach_list(request):
    status_filter = request.GET.get("status", "")
    qs = _threads(request).select_related("target_company").order_by("-created_at")
    if status_filter == "interested":
        qs = qs.filter(classification="interested")
    elif status_filter:
        qs = qs.filter(status=status_filter)

    counts = {
        "all": _threads(request).count(),
        "drafted": _threads(request).filter(status="drafted").count(),
        "sent": _threads(request).filter(status="sent").count(),
        "replied": _threads(request).filter(status="replied").count(),
        "interested": _threads(request).filter(classification="interested").count(),
        "closed": _threads(request).filter(status="closed").count(),
    }

    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(request.GET.get("page"))
    context = {"page_obj": page_obj, "counts": counts, "status_filter": status_filter}
    return render(request, "dashboard/outreach.html", context)


def thread_detail(request, pk):
    thread = get_object_or_404(_threads(request), pk=pk)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "save_draft":
            body = request.POST.get("body", "").strip()
            if body:
                EmailMessage.objects.create(thread=thread, direction="outbound", body=body)
                messages.success(request, "Draft saved.")
            return redirect("thread_detail", pk=pk)

        elif action in ("send", "generate_ai_reply") and not request.user.is_superuser:
            messages.error(request, "Sending and AI replies use the platform mailbox and are not available on your account yet.")
            return redirect("thread_detail", pk=pk)

        elif action == "send":
            body = request.POST.get("body", "").strip()
            if body:
                EmailMessage.objects.create(thread=thread, direction="outbound", body=body)
            try:
                from mailbox_app.tasks import send_email_task
                send_email_task.delay(thread.id)
                messages.success(request, "Send queued. Guardrails and rate limits will apply before it actually goes out.")
            except Exception as e:
                messages.error(request, f"Could not queue send: {e}")
            return redirect("thread_detail", pk=pk)

        elif action == "generate_ai_reply":
            try:
                from agent.services.reply_handling import draft_reply
                draft = draft_reply(thread)
                request.session[f"ai_draft_{pk}"] = draft.body
                messages.success(request, "AI draft generated below. Review before sending.")
            except Exception as e:
                messages.error(request, f"AI draft failed: {e}")
            return redirect("thread_detail", pk=pk)

    ai_draft = request.session.pop(f"ai_draft_{pk}", None)
    context = {"thread": thread, "ai_draft": ai_draft}
    return render(request, "dashboard/thread_detail.html", context)


def products_page(request):
    tab = request.GET.get("tab", "products")
    company = _default_company(request)
    context = {
        "tab": tab,
        "products": Product.objects.filter(company=company),
        "services": Service.objects.filter(company=company),
        "portfolio_items": PortfolioItem.objects.filter(company=company),
    }
    return render(request, "dashboard/products.html", context)


def product_add(request, pk=None):
    company = _default_company(request)
    instance = get_object_or_404(Product, pk=pk, company=company) if pk else None
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        price_note = request.POST.get("price_note", "").strip()
        if instance:
            instance.name, instance.description, instance.price_note = name, description, price_note
            instance.save()
            messages.success(request, "Product updated.")
        else:
            Product.objects.create(company=company, name=name, description=description, price_note=price_note)
            messages.success(request, "Product added.")
        return redirect("/products/?tab=products")
    return render(request, "dashboard/item_form.html", {"instance": instance, "item_type": "Product", "back_url": "/products/?tab=products", "show_price": True})


def product_delete(request, pk):
    Product.objects.filter(pk=pk, company__owner=request.user).delete()
    messages.success(request, "Product deleted.")
    return redirect("/products/?tab=products")


def product_toggle(request, pk):
    p = get_object_or_404(Product, pk=pk, company__owner=request.user)
    p.is_active = not p.is_active
    p.save()
    return redirect("/products/?tab=products")


def service_add(request, pk=None):
    company = _default_company(request)
    instance = get_object_or_404(Service, pk=pk, company=company) if pk else None
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        target_signal = request.POST.get("target_signal", "").strip()
        if instance:
            instance.name, instance.description, instance.target_signal = name, description, target_signal
            instance.save()
            messages.success(request, "Service updated.")
        else:
            Service.objects.create(company=company, name=name, description=description, target_signal=target_signal)
            messages.success(request, "Service added.")
        return redirect("/products/?tab=services")
    return render(request, "dashboard/item_form.html", {"instance": instance, "item_type": "Service", "back_url": "/products/?tab=services", "show_target_signal": True})


def service_delete(request, pk):
    Service.objects.filter(pk=pk, company__owner=request.user).delete()
    messages.success(request, "Service deleted.")
    return redirect("/products/?tab=services")


def service_toggle(request, pk):
    s = get_object_or_404(Service, pk=pk, company__owner=request.user)
    s.is_active = not s.is_active
    s.save()
    return redirect("/products/?tab=services")


def portfolio_add(request, pk=None):
    company = _default_company(request)
    instance = get_object_or_404(PortfolioItem, pk=pk, company=company) if pk else None
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        summary = request.POST.get("summary", "").strip()
        if instance:
            instance.title, instance.summary = title, summary
            instance.save()
            messages.success(request, "Portfolio item updated.")
        else:
            PortfolioItem.objects.create(company=company, title=title, summary=summary)
            messages.success(request, "Portfolio item added.")
        return redirect("/products/?tab=portfolio")
    return render(request, "dashboard/item_form.html", {"instance": instance, "item_type": "Portfolio Item", "back_url": "/products/?tab=portfolio", "is_portfolio": True})


def portfolio_delete(request, pk):
    PortfolioItem.objects.filter(pk=pk, company__owner=request.user).delete()
    messages.success(request, "Portfolio item deleted.")
    return redirect("/products/?tab=portfolio")


def sales_rules_page(request):
    company = _default_company(request)
    rules = SalesRule.objects.filter(company=company)
    return render(request, "dashboard/sales_rules.html", {"rules": rules})


def sales_rule_add(request, pk=None):
    company = _default_company(request)
    instance = get_object_or_404(SalesRule, pk=pk, company=company) if pk else None
    if request.method == "POST":
        rule_text = request.POST.get("rule_text", "").strip()
        if instance:
            instance.rule_text = rule_text
            instance.save()
            messages.success(request, "Rule updated.")
        else:
            SalesRule.objects.create(company=company, rule_text=rule_text)
            messages.success(request, "Rule added.")
        return redirect("sales_rules")
    return render(request, "dashboard/rule_form.html", {"instance": instance})


def sales_rule_delete(request, pk):
    SalesRule.objects.filter(pk=pk, company__owner=request.user).delete()
    messages.success(request, "Rule deleted.")
    return redirect("sales_rules")


def proposals_page(request):
    company = _default_company(request)
    templates = ProposalTemplate.objects.filter(company=company)
    return render(request, "dashboard/proposals.html", {"templates": templates})


def proposal_add(request, pk=None):
    company = _default_company(request)
    instance = get_object_or_404(ProposalTemplate, pk=pk, company=company) if pk else None
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        template_text = request.POST.get("template_text", "").strip()
        if instance:
            instance.name, instance.template_text = name, template_text
            instance.save()
            messages.success(request, "Template updated.")
        else:
            ProposalTemplate.objects.create(company=company, name=name, template_text=template_text)
            messages.success(request, "Template created.")
        return redirect("proposals")
    return render(request, "dashboard/proposal_form.html", {"instance": instance})


def proposal_duplicate(request, pk):
    company = _default_company(request)
    original = get_object_or_404(ProposalTemplate, pk=pk, company=company)
    ProposalTemplate.objects.create(company=company, name=f"{original.name} (Copy)", template_text=original.template_text)
    messages.success(request, "Template duplicated.")
    return redirect("proposals")


def proposal_delete(request, pk):
    ProposalTemplate.objects.filter(pk=pk, company__owner=request.user).delete()
    messages.success(request, "Template deleted.")
    return redirect("proposals")


@_staff_only
def ai_agent_page(request):
    tab = request.GET.get("tab", "overview")
    total_invocations = AgentInvocation.objects.count()
    total_tokens = AgentInvocation.objects.aggregate(t=Sum("tokens_in"), o=Sum("tokens_out"))
    tokens_in = total_tokens["t"] or 0
    tokens_out = total_tokens["o"] or 0
    total_cost = AgentInvocation.objects.aggregate(c=Sum("cost_usd"))["c"] or 0

    recent_invocations = AgentInvocation.objects.order_by("-created_at")[:8]
    last_company = _co(request).order_by("-created_at").first()

    if tab == "logs":
        qs = AgentInvocation.objects.order_by("-created_at")
        paginator = Paginator(qs, 20)
        page_obj = paginator.get_page(request.GET.get("page"))
    else:
        page_obj = None

    context = {
        "tab": tab,
        "agent_running": _celery_is_running(),
        "total_invocations": total_invocations,
        "tokens_in": tokens_in, "tokens_out": tokens_out,
        "total_cost": total_cost,
        "recent_invocations": recent_invocations,
        "last_company": last_company,
        "page_obj": page_obj,
    }
    return render(request, "dashboard/ai_agent.html", context)


@_staff_only
def prompts_page(request):
    prompts = PromptTemplate.objects.all().order_by("key", "-version")
    return render(request, "dashboard/prompts.html", {"prompts": prompts})


@_staff_only
def prompt_toggle(request, pk):
    p = get_object_or_404(PromptTemplate, pk=pk)
    p.is_active = not p.is_active
    p.save()
    return redirect("prompts")


@_staff_only
def compliance_page(request):
    tab = request.GET.get("tab", "overview")
    suppressed_count = SuppressedContact.objects.count()
    audit_count = AuditLog.objects.count()
    skipped_replies = AuditLog.objects.filter(action="skip_unmatched_reply").count()
    recent_audits = AuditLog.objects.order_by("-created_at")[:8]

    if tab == "suppressed":
        qs = SuppressedContact.objects.order_by("-added_at")
        paginator = Paginator(qs, 20)
        page_obj = paginator.get_page(request.GET.get("page"))
    elif tab == "audit":
        qs = AuditLog.objects.order_by("-created_at")
        paginator = Paginator(qs, 20)
        page_obj = paginator.get_page(request.GET.get("page"))
    else:
        page_obj = None

    context = {
        "tab": tab, "suppressed_count": suppressed_count, "audit_count": audit_count,
        "skipped_replies": skipped_replies, "recent_audits": recent_audits, "page_obj": page_obj,
    }
    return render(request, "dashboard/compliance.html", context)


def prospecting_page(request):
    niches = _niches(request).all().order_by("niche_name", "region")
    for n in niches:
        n.found_count = n.companies_found.count()
    active_count = _niches(request).filter(active=True).count()
    total_companies = _co(request).count()
    context = {"niches": niches, "active_count": active_count, "total_companies": total_companies}
    return render(request, "dashboard/prospecting.html", context)


def niche_add(request, pk=None):
    instance = get_object_or_404(_niches(request), pk=pk) if pk else None
    if request.method == "POST":
        niche_name = request.POST.get("niche_name", "").strip()
        region = request.POST.get("region", "").strip()
        if instance:
            instance.niche_name, instance.region = niche_name, region
            instance.save()
            messages.success(request, "Niche updated.")
        else:
            NicheConfig.objects.create(owner=request.user, niche_name=niche_name, region=region, active=True)
            messages.success(request, "Niche added.")
        return redirect("prospecting")
    return render(request, "dashboard/niche_form.html", {"instance": instance})


def niche_toggle(request, pk):
    n = get_object_or_404(_niches(request), pk=pk)
    n.active = not n.active
    n.save()
    return redirect("prospecting")


def niche_delete(request, pk):
    _niches(request).filter(pk=pk).delete()
    messages.success(request, "Niche removed.")
    return redirect("prospecting")


def reports_page(request):
    tab = request.GET.get("tab", "overview")
    range_param = request.GET.get("range", "7")

    today = timezone.localdate()
    if range_param == "today":
        start = today
    elif range_param == "30":
        start = today - timedelta(days=29)
    else:
        start = today - timedelta(days=6)

    businesses_found = _co(request).filter(created_at__date__gte=start, created_at__date__lte=today).count()
    emails_sent = _msgs(request).filter(direction="outbound", sent_at__date__gte=start, sent_at__date__lte=today).count()
    replies = _msgs(request).filter(direction="inbound", created_at__date__gte=start, created_at__date__lte=today).count()
    interested = _threads(request).filter(classification="interested", created_at__date__gte=start, created_at__date__lte=today).count()
    reply_rate = round((replies / emails_sent) * 100) if emails_sent > 0 else 0

    top_companies = _co(request).filter(status__in=["replied", "sent"]).order_by("-created_at")[:5]
    recent_replies = _msgs(request).filter(direction="inbound", created_at__date__gte=start).select_related("thread__target_company").order_by("-created_at")[:5]
    interested_leads = _threads(request).filter(classification="interested").select_related("target_company").order_by("-created_at")[:5]

    if tab == "digests" and request.user.is_superuser:
        qs = DailyDigest.objects.order_by("-date")
        paginator = Paginator(qs, 15)
        page_obj = paginator.get_page(request.GET.get("page"))
    else:
        page_obj = None

    context = {
        "tab": tab, "range": range_param,
        "businesses_found": businesses_found, "emails_sent": emails_sent,
        "replies": replies, "interested": interested, "reply_rate": reply_rate,
        "top_companies": top_companies, "recent_replies": recent_replies,
        "interested_leads": interested_leads, "page_obj": page_obj,
    }
    return render(request, "dashboard/reports.html", context)


@_staff_only
def digest_detail(request, date):
    digest = get_object_or_404(DailyDigest, date=date)
    return render(request, "dashboard/digest_detail.html", {"digest": digest})


def research_page(request):
    company_id = request.GET.get("company_id")
    selected_company = None
    research = None

    if company_id:
        selected_company = get_object_or_404(_co(request), pk=company_id)
        research = getattr(selected_company, "research_result", None)

    if request.method == "POST" and request.POST.get("action") == "run_research" and not request.user.is_superuser:
        messages.error(request, "Manual research is limited to the platform administrator for now. Research runs automatically on discovered companies.")
    elif request.method == "POST" and request.POST.get("action") == "run_research":
        target_id = request.POST.get("company_id")
        selected_company = get_object_or_404(_co(request), pk=target_id)
        try:
            from agent.services.research import research_company
            from agent.services.interfaces import ResearchInput
            result = research_company(ResearchInput(
                company_name=selected_company.name,
                domain=selected_company.domain or "",
                country=selected_company.country or "",
            ))
            ResearchResult.objects.update_or_create(
                target_company=selected_company,
                defaults={
                    "has_website": result.has_website,
                    "detected_industry": result.detected_industry,
                    "detected_tools": result.detected_tools,
                    "summary": result.summary,
                },
            )
            selected_company.status = "researched"
            selected_company.save(update_fields=["status"])
            messages.success(request, "Research completed and saved.")
        except Exception as e:
            messages.error(request, f"Research failed: {e}")
        research = getattr(selected_company, "research_result", None)

    q = request.GET.get("q", "").strip()
    companies_qs = _co(request).all().order_by("-created_at")
    if q:
        companies_qs = companies_qs.filter(Q(name__icontains=q) | Q(domain__icontains=q))
    companies_qs = companies_qs[:30]

    context = {"companies": companies_qs, "selected_company": selected_company, "research": research, "q": q}
    return render(request, "dashboard/research.html", context)


def settings_page(request):
    tab = request.GET.get("tab", "general")
    company = _default_company(request)

    if request.method == "POST" and tab == "general":
        company.name = request.POST.get("name", "").strip()
        company.description = request.POST.get("description", "").strip()
        company.based_in = request.POST.get("based_in", "").strip()
        company.email_tone = request.POST.get("email_tone", "").strip()
        company.save()
        messages.success(request, "Company settings saved.")
        return redirect("/settings/?tab=general")

    import os
    token_path = getattr(django_settings, "BASE_DIR", None)
    gmail_token_exists = os.path.exists("gmail_token.json")

    anthropic_key = getattr(django_settings, "ANTHROPIC_API_KEY", "")
    placeholder_values = ["", "paste-your-real-key-here", "placeholder-key-add-real-one-later"]
    anthropic_configured = anthropic_key not in placeholder_values

    context = {
        "tab": tab,
        "company": company,
        "gmail_connected": gmail_token_exists,
        "anthropic_configured": anthropic_configured,
        "rate_limit": getattr(django_settings, "SEND_RATE_LIMIT_PER_HOUR", "-"),
        "report_email": getattr(django_settings, "REPORT_RECIPIENT_EMAIL", "-"),
    }
    return render(request, "dashboard/settings.html", context)


def landing_page(request):
    stats = {
        "companies_found": TargetCompany.objects.count(),
        "emails_sent": EmailMessage.objects.filter(direction="outbound", sent_at__isnull=False).count(),
        "replies": EmailMessage.objects.filter(direction="inbound").count(),
    }
    return render(request, "dashboard/landing.html", {"stats": stats})


def signup_page(request):
    from django.contrib.auth import login
    from .forms import SignUpForm

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("dashboard")
    else:
        form = SignUpForm()
    return render(request, "dashboard/signup.html", {"form": form})


def _get_or_create_candidate_profile(user):
    from jobs.models import CandidateProfile
    profile, _ = CandidateProfile.objects.get_or_create(user=user)
    return profile


def candidate_profile_page(request):
    from jobs.models import Skill, Experience, JobSearchConfig, JobListing

    profile = _get_or_create_candidate_profile(request.user) if request.user.is_authenticated else None
    if not profile:
        messages.error(request, "You must be logged in to manage your candidate profile.")
        return redirect("login")

    tab = request.GET.get("tab", "profile")

    if request.method == "POST" and tab == "profile":
        profile.summary = request.POST.get("summary", "").strip()
        profile.years_experience = request.POST.get("years_experience", "0") or 0
        profile.preferred_roles = request.POST.get("preferred_roles", "").strip()
        profile.preferred_regions = request.POST.get("preferred_regions", "").strip()
        profile.remote_preference = request.POST.get("remote_preference", "remote_preferred")
        if request.FILES.get("cv_file"):
            profile.cv_file = request.FILES["cv_file"]
        profile.save()
        messages.success(request, "Profile updated.")
        return redirect("/jobs/profile/?tab=profile")

    if request.method == "POST" and tab == "listings" and request.POST.get("action") == "run_discovery":
        try:
            from jobs.tasks import discover_jobs_task
            result = discover_jobs_task.delay(request.user.id)
            messages.success(request, "Job discovery queued. Refresh in a moment to see new listings.")
        except Exception as e:
            messages.error(request, f"Could not queue discovery: {e}")
        return redirect("/jobs/profile/?tab=listings")

    context = {
        "tab": tab,
        "profile": profile,
        "skills": Skill.objects.filter(profile=profile),
        "experiences": Experience.objects.filter(profile=profile),
        "job_configs": JobSearchConfig.objects.filter(user=request.user),
        "job_listings": JobListing.objects.filter(config__user=request.user).order_by("-created_at")[:50],
    }
    return render(request, "dashboard/candidate_profile.html", context)


def job_config_add(request, pk=None):
    from jobs.models import JobSearchConfig
    instance = get_object_or_404(JobSearchConfig, pk=pk, user=request.user) if pk else None
    prefill_role = request.GET.get("role_query", "")
    prefill_region = request.GET.get("region", "")
    if request.method == "POST":
        role_query = request.POST.get("role_query", "").strip()
        region = request.POST.get("region", "").strip()
        if instance:
            instance.role_query, instance.region = role_query, region
            instance.save()
            messages.success(request, "Search updated.")
        else:
            JobSearchConfig.objects.create(user=request.user, role_query=role_query, region=region, active=True)
            messages.success(request, "Job search added.")
        return redirect("/jobs/profile/?tab=config")
    return render(request, "dashboard/job_config_form.html", {"instance": instance, "prefill_role": prefill_role, "prefill_region": prefill_region})


def job_config_toggle(request, pk):
    from jobs.models import JobSearchConfig
    c = get_object_or_404(JobSearchConfig, pk=pk, user=request.user)
    c.active = not c.active
    c.save()
    return redirect("/jobs/profile/?tab=config")


def job_config_delete(request, pk):
    from jobs.models import JobSearchConfig
    JobSearchConfig.objects.filter(pk=pk, user=request.user).delete()
    messages.success(request, "Job search removed.")
    return redirect("/jobs/profile/?tab=config")


def job_listing_status(request, pk):
    from jobs.models import JobListing
    listing = get_object_or_404(JobListing, pk=pk, config__user=request.user)
    new_status = request.POST.get("status")
    if new_status in dict(JobListing.STATUS_CHOICES):
        listing.status = new_status
        listing.save()
        messages.success(request, "Status updated.")
    return redirect("/jobs/profile/?tab=listings")


def skill_add(request, pk=None):
    from jobs.models import Skill
    profile = _get_or_create_candidate_profile(request.user)
    instance = get_object_or_404(Skill, pk=pk, profile=profile) if pk else None
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        proficiency = request.POST.get("proficiency", "intermediate")
        years = request.POST.get("years", "0") or 0
        if instance:
            instance.name, instance.proficiency, instance.years = name, proficiency, years
            instance.save()
            messages.success(request, "Skill updated.")
        else:
            Skill.objects.create(profile=profile, name=name, proficiency=proficiency, years=years)
            messages.success(request, "Skill added.")
        return redirect("/jobs/profile/?tab=skills")
    return render(request, "dashboard/skill_form.html", {"instance": instance})


def skill_delete(request, pk):
    from jobs.models import Skill
    profile = _get_or_create_candidate_profile(request.user)
    Skill.objects.filter(pk=pk, profile=profile).delete()
    messages.success(request, "Skill removed.")
    return redirect("/jobs/profile/?tab=skills")


def experience_add(request, pk=None):
    from jobs.models import Experience
    profile = _get_or_create_candidate_profile(request.user)
    instance = get_object_or_404(Experience, pk=pk, profile=profile) if pk else None
    if request.method == "POST":
        company = request.POST.get("company", "").strip()
        role = request.POST.get("role", "").strip()
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date") or None
        description = request.POST.get("description", "").strip()
        if instance:
            instance.company, instance.role = company, role
            instance.start_date, instance.end_date = start_date, end_date
            instance.description = description
            instance.save()
            messages.success(request, "Experience updated.")
        else:
            Experience.objects.create(profile=profile, company=company, role=role, start_date=start_date, end_date=end_date, description=description)
            messages.success(request, "Experience added.")
        return redirect("/jobs/profile/?tab=experience")
    return render(request, "dashboard/experience_form.html", {"instance": instance})


def experience_delete(request, pk):
    from jobs.models import Experience
    profile = _get_or_create_candidate_profile(request.user)
    Experience.objects.filter(pk=pk, profile=profile).delete()
    messages.success(request, "Experience removed.")
    return redirect("/jobs/profile/?tab=experience")


def job_listing_generate_notes(request, pk):
    from jobs.models import JobListing

    listing = get_object_or_404(JobListing, pk=pk, config__user=request.user)
    if request.method == "POST":
        try:
            from jobs.services.application_drafting import draft_talking_points
            profile = _get_or_create_candidate_profile(request.user)
            notes = draft_talking_points(profile, listing)
            listing.ai_talking_points = notes
            listing.save()
            messages.success(request, "Talking points generated.")
        except Exception as e:
            messages.error(request, f"Could not generate talking points: {e}")
    return redirect("/jobs/profile/?tab=listings")


def job_config_add_recommended(request):
    from jobs.models import JobSearchConfig

    if request.method != "POST":
        return redirect("/jobs/profile/?tab=config")

    profile = _get_or_create_candidate_profile(request.user)
    base_role = profile.preferred_roles.strip() or "remote job"
    base_region = profile.preferred_regions.strip() or "remote worldwide"

    presets = [
        ("general", base_role, base_region),
        ("ai_training", "AI trainer OR annotation OR data labeling", "site:jobs.micro1.ai"),
        ("startup", f"{base_role} startup", "remote"),
        ("internship", f"{base_role} internship", "remote internship"),
        ("visa_sponsorship", f"{base_role} visa sponsorship OR relocation", base_region),
        ("ngo", "NGO OR humanitarian OR international development jobs", "Ghana"),
        ("ngo", f"{base_role} health OR humanitarian", "site:reliefweb.int OR site:devex.com OR site:idealist.org"),
        ("general", base_role, "site:linkedin.com/jobs"),
    ]

    created = 0
    for category, role_query, region in presets:
        obj, was_created = JobSearchConfig.objects.get_or_create(
            user=request.user, role_query=role_query, region=region,
            defaults={"active": True, "category": category},
        )
        if was_created:
            created += 1

    messages.success(
        request,
        f"Added {created} recommended searches. Note: internship and visa-sponsorship results only "
        "surface listings that explicitly mention this - not every relevant employer states it upfront."
    )
    return redirect("/jobs/profile/?tab=config")
