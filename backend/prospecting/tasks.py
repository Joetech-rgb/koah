import re
from concurrent.futures import ThreadPoolExecutor, wait as _wait

from celery import shared_task
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import F, Q
from django.utils import timezone

from .models import NicheConfig
from .catalog import BROAD_NICHES, CATALOG, NICHE_PLAYBOOKS
from .services.discovery import find_businesses, find_places, find_facebook_pages, find_social_profiles
from .services.contact_extraction import extract_contact_email, extract_contact_phone
from crm.models import TargetCompany

DEFAULT_REGION = "Ghana"
MAX_NEW_PER_RUN = 30
TENANT_MAX_NEW_PER_RUN = 12
PER_NICHE_CAP = 6
DAILY_AI_RESEARCH_CAP = 40
TENANT_DAILY_AI_CAP = 10
TENANT_MAX_NICHES = 3
AUTO_NICHES_PER_RUN = 4
SOURCE_FUNCS = {"web": find_businesses, "places": find_places, "facebook": find_facebook_pages, "social": find_social_profiles}

JUNK_WORDS = ("for sale", "used cars", "from china", "top 10", "top 5", "how to", "classifieds", "(with photos)",
              "restaurants in", "locations & branches", "business directory", "listings", "near me",
              "start your own", "replies by", "immigration", "ministry of", "overview",
              "bank of ", "statistical service", "location in")
JUNK_EXACT = {"contact", "contact us", "home", "about", "about us", "menu", "talk to us", "get in touch"}
JUNK_PREFIXES = ("top ", "best ", "start ", "how ")
EXTRA_PLAYBOOKS = {
    "it services": "Custom software, AI automation, internal tools and dashboards, networking and managed IT. Position as a development partner for their projects.",
}

_POOL = ThreadPoolExecutor(max_workers=8)


# ---------- owner helpers ----------
def _is_admin(owner):
    return owner is None or owner.is_superuser


def _cap_for(owner):
    return DAILY_AI_RESEARCH_CAP if _is_admin(owner) else TENANT_DAILY_AI_CAP


def _cap_key(owner):
    return "ai_research_count:%s:%s" % (owner.id if owner else 0, timezone.now().date())


def _brain_ready(owner):
    from brain.models import CompanyProfile, Service, Product
    company = CompanyProfile.objects.filter(owner=owner).first()
    if not company:
        return False
    return (Service.objects.filter(company=company, is_active=True).exists()
            or Product.objects.filter(company=company, is_active=True).exists())


def _catalog_for(owner, company):
    """KoahCloud's own catalog for admins; built from their Products and Services for tenants."""
    if _is_admin(owner):
        return CATALOG, False
    from brain.models import Service, Product
    items = []
    if company:
        for s in Service.objects.filter(company=company, is_active=True):
            items.append({"offer": s.name + (" - " + s.description[:150] if s.description else ""),
                          "fits": s.target_signal or "any organization"})
        for p in Product.objects.filter(company=company, is_active=True):
            items.append({"offer": p.name + (" - " + p.description[:150] if p.description else ""),
                          "fits": "any organization"})
    return items, True


# ---------- cleaning and filtering ----------
def _enrich(domain, timeout=12):
    """Run email and phone extraction in parallel with a hard cap, so one dead domain cannot hang the run."""
    fe = _POOL.submit(extract_contact_email, domain)
    fp = _POOL.submit(extract_contact_phone, domain)
    _wait([fe, fp], timeout=timeout)

    def _get(f):
        try:
            return f.result(timeout=0) if f.done() else None
        except Exception:
            return None
    return _get(fe), _get(fp)


def _clean_email(e):
    if not e:
        return None
    m = re.match(r"^([A-Za-z0-9._%+\-]+@(?:[A-Za-z0-9\-]+\.)+?(?:com\.gh|org\.gh|edu\.gh|gov\.gh|com\.ng|co\.uk|co\.za|com|org|net|gh|ng|uk|io|co|info|biz|edu|gov|africa|tech|app|dev|online|store))(?![a-z])", e)
    if m:
        return m.group(1).lower()
    e2 = e.strip()
    return e2.lower() if re.fullmatch(r"[A-Za-z0-9._%+\-]+@[a-z0-9\-]+(\.[a-z0-9\-]+)+", e2) else None


def _clean_phone(p):
    if not p:
        return p
    p = re.sub(r"[()]", "", p)
    return re.sub(r"\s+", " ", p).strip()


def _fix_name(c):
    """Turn bare page titles like 'Contact us' into a usable name, using the domain."""
    n = (c.get("name") or "").strip()
    low = n.lower()
    domain = c.get("domain")
    if low.startswith("contact ") and low not in JUNK_EXACT:
        n = n[8:].strip()
    elif low in JUNK_EXACT and domain:
        n = re.sub(r"[-_]+", " ", domain.split(".")[0]).title()
    c["name"] = n


def _is_junk(c):
    _fix_name(c)
    name = (c.get("name") or "").lower().strip()
    return (not name) or name in JUNK_EXACT or name.startswith(JUNK_PREFIXES) or any(w in name for w in JUNK_WORDS)


def _playbook_for(niche):
    if not niche:
        return ""
    if niche.playbook:
        return niche.playbook
    if not _is_admin(niche.owner):
        return ""
    n = niche.niche_name.lower().strip()
    if n in EXTRA_PLAYBOOKS:
        return EXTRA_PLAYBOOKS[n]
    if "car wash" in n:
        return NICHE_PLAYBOOKS.get("car washes", "")
    return NICHE_PLAYBOOKS.get(n) or NICHE_PLAYBOOKS.get(n + "s") or ""


def _channel_for(tc):
    if tc.contact_email:
        return "email"
    if tc.contact_phone:
        return "phone"
    if tc.facebook_url:
        return "facebook"
    if tc.social_url:
        return "social"
    return "none"


def _website_status(c):
    if c.get("domain"):
        return "has_website"
    if c.get("source") in ("facebook", "social") or c.get("facebook_url") or c.get("social_url"):
        return "social_only"
    return "none"


# ---------- pitch pipeline ----------
@shared_task
def draft_pitch_task(target_company_id):
    from agent.services.interfaces import DraftInput, ResearchOutput
    from agent.services.drafting import draft_pitch
    from brain.models import CompanyProfile, Service, Product, SalesRule
    from crm.models import ResearchResult
    from outreach.models import EmailThread, EmailMessage

    target_company = TargetCompany.objects.select_related("owner", "source_niche").get(id=target_company_id)
    if EmailThread.objects.filter(target_company=target_company).exists():
        return "skipped: draft already exists"
    research_result = ResearchResult.objects.get(target_company=target_company)
    owner = target_company.owner

    research_output = ResearchOutput(
        has_website=research_result.has_website,
        detected_industry=research_result.detected_industry,
        detected_tools=research_result.detected_tools,
        summary=research_result.summary,
        confidence=1.0,
    )

    company = CompanyProfile.objects.filter(owner=owner).first() if owner else CompanyProfile.objects.first()
    brain_context = {"country": target_company.country}
    if company:
        brain_context["company"] = {
            "name": company.name,
            "description": company.description,
            "email_tone": company.email_tone,
            "phone": company.phone,
            "based_in": company.based_in,
        }
        brain_context["services"] = list(Service.objects.filter(company=company, is_active=True).values("name", "description"))
        brain_context["products"] = list(Product.objects.filter(company=company, is_active=True).values("name", "description"))
        brain_context["sales_rules"] = list(SalesRule.objects.filter(company=company).values_list("rule_text", flat=True))

    catalog, generic = _catalog_for(owner, company)
    brain_context["catalog"] = catalog
    brain_context["prospect"] = {
        "org_type": target_company.org_type,
        "name": target_company.name,
        "playbook": _playbook_for(target_company.source_niche),
        "website_status": target_company.website_status,
        "facebook_url": target_company.facebook_url,
        "address": target_company.contact_address,
        "channel": _channel_for(target_company),
        "email": target_company.contact_email,
        "phone": target_company.contact_phone,
        "social_url": target_company.social_url,
        "generic_angle": generic,
    }

    draft_output = draft_pitch(DraftInput(research=research_output, brain_context=brain_context))

    thread = EmailThread.objects.create(
        target_company=target_company,
        subject=draft_output.subject,
        pitch_angle=draft_output.pitch_angle,
        status="drafted",
    )
    EmailMessage.objects.create(thread=thread, direction="outbound", body=draft_output.body)

    target_company.status = "drafted"
    target_company.save()
    return thread.id


def _research_label(tc):
    bits = [tc.org_type, tc.contact_address, ("Facebook: " + tc.facebook_url if tc.facebook_url else None),
            ("Social: " + tc.social_url if tc.social_url else None)]
    extra = ", ".join(b for b in bits if b)
    return "%s (%s)" % (tc.name, extra) if extra else tc.name


@shared_task
def research_company_task(target_company_id):
    from django.core.cache import cache
    from agent.services.interfaces import ResearchInput
    from agent.services.research import research_company
    from crm.models import ResearchResult
    try:
        from agent.services.qualify import qualify_company
    except ImportError:
        def qualify_company(tc):
            return True, "qualify module missing"

    target_company = TargetCompany.objects.select_related("owner", "source_niche").get(id=target_company_id)
    owner = target_company.owner

    if target_company.status != "new":
        return "skipped: already " + target_company.status

    key = _cap_key(owner)
    cache.add(key, 0, 93600)
    if (cache.get(key) or 0) >= _cap_for(owner):
        return "daily AI cap reached"
    if not _is_admin(owner) and not _brain_ready(owner):
        return "add at least one product or service first"

    ok, why = qualify_company(target_company)
    if not ok:
        target_company.status = "rejected"
        target_company.save(update_fields=["status"])
        return "rejected: " + why

    research_input = ResearchInput(
        company_name=_research_label(target_company),
        domain=target_company.domain,
        country=target_company.country,
    )
    research_output = research_company(research_input)
    cache.incr(key)

    ResearchResult.objects.update_or_create(
        target_company=target_company,
        defaults={
            "has_website": (target_company.website_status == "has_website") if target_company.website_status != "unknown" else research_output.has_website,
            "detected_industry": research_output.detected_industry,
            "detected_tools": research_output.detected_tools,
            "summary": research_output.summary,
        },
    )
    target_company.industry = research_output.detected_industry
    target_company.status = "researched"
    target_company.save()

    draft_pitch_task.delay(target_company.id)
    return target_company.id


# ---------- discovery ----------
def _pick_niches(owner):
    manual = list(NicheConfig.objects.filter(owner=owner, active=True).order_by(F("last_searched_at").asc(nulls_first=True)))
    if not owner.is_superuser:
        return manual[:TENANT_MAX_NICHES]
    region = manual[0].region if manual else DEFAULT_REGION
    for name in BROAD_NICHES:
        NicheConfig.objects.get_or_create(owner=owner, niche_name=name, region=region, defaults={"active": False})
    manual_ids = [n.id for n in manual]
    auto = (NicheConfig.objects.filter(owner=owner, niche_name__in=BROAD_NICHES, region=region)
            .exclude(id__in=manual_ids)
            .order_by(F("last_searched_at").asc(nulls_first=True))[:AUTO_NICHES_PER_RUN])
    return manual + list(auto)


def _find_existing(c, owner):
    """Match within this owner's companies: domain, Google CID, Facebook URL, social URL, then name + phone."""
    qs = TargetCompany.objects.filter(owner=owner)
    domain = c.get("domain")
    if domain:
        m = qs.filter(domain__in=[domain, "www." + domain]).first()
        if m:
            return m
    if c.get("google_cid"):
        m = qs.filter(google_cid=c["google_cid"]).first()
        if m:
            return m
    if c.get("facebook_url"):
        m = qs.filter(facebook_url=c["facebook_url"]).first()
        if m:
            return m
    if c.get("social_url"):
        m = qs.filter(social_url=c["social_url"]).first()
        if m:
            return m
    phone = c.get("phone")
    if phone and c.get("name"):
        m = qs.filter(contact_phone=phone, name__iexact=c["name"]).first()
        if m:
            return m
    return None


def _discover_for_owner(owner):
    created_ids = []
    limit = MAX_NEW_PER_RUN if _is_admin(owner) else TENANT_MAX_NEW_PER_RUN
    for niche in _pick_niches(owner):
        if len(created_ids) >= limit:
            break
        sources = niche.sources or ["web", "places", "facebook", "social"]
        niche_start = len(created_ids)
        for source in sources:
            if len(created_ids) >= limit:
                break
            func = SOURCE_FUNCS.get(source)
            if not func:
                continue
            try:
                candidates = func(niche.niche_name, niche.region)
            except Exception:
                continue

            for c in candidates:
                if len(created_ids) >= limit:
                    break
                if len(created_ids) - niche_start >= PER_NICHE_CAP:
                    break
                if not c.get("name"):
                    continue
                if _is_junk(c):
                    continue
                if _find_existing(c, owner):
                    continue
                try:
                    with transaction.atomic():
                        target_company = TargetCompany.objects.create(
                            owner=owner,
                            name=c["name"][:255],
                            domain=c.get("domain") or None,
                            country=niche.region,
                            status="new",
                            source_niche=niche,
                            contact_phone=(c.get("phone") or None),
                            contact_address=c.get("address") or None,
                            google_cid=c.get("google_cid") or None,
                            facebook_url=c.get("facebook_url") or None,
                            social_url=c.get("social_url") or None,
                            social_platform=c.get("social_platform") or None,
                            org_type=(c.get("category") or niche.niche_name)[:100],
                            website_status=_website_status(c),
                            discovery_source=c.get("source"),
                        )
                except IntegrityError:
                    continue

                domain = target_company.domain
                if domain:
                    try:
                        email, phone = _enrich(domain)
                        email = _clean_email(email)
                        phone = _clean_phone(phone)
                    except Exception:
                        email, phone = None, None
                    if email:
                        target_company.contact_email = email
                    if phone and not target_company.contact_phone:
                        target_company.contact_phone = phone
                    if email or phone:
                        target_company.save()

                created_ids.append(target_company.id)
                research_company_task.delay(target_company.id)

        niche.last_searched_at = timezone.now()
        niche.save(update_fields=["last_searched_at"])
    return created_ids


@shared_task
def discover_companies_task():
    User = get_user_model()
    owner_ids = list(NicheConfig.objects.filter(active=True, owner__isnull=False).values_list("owner_id", flat=True).distinct())
    created_ids = []
    for owner in User.objects.filter(Q(id__in=owner_ids) | Q(is_superuser=True), is_active=True):
        created_ids.extend(_discover_for_owner(owner))
    return created_ids


@shared_task
def requeue_new_task(limit=None):
    """Re-trigger research for companies stuck at 'new', per owner, reachable prospects first."""
    from django.core.cache import cache
    User = get_user_model()
    rank = {"email": 0, "phone": 1, "facebook": 2, "social": 2, "none": 3}
    ids = []
    for oid in set(TargetCompany.objects.filter(status="new").values_list("owner_id", flat=True)):
        owner = User.objects.filter(id=oid).first() if oid else None
        room = max(0, _cap_for(owner) - (cache.get(_cap_key(owner)) or 0))
        if limit is not None:
            room = min(room, limit)
        pool = sorted(TargetCompany.objects.filter(status="new", owner_id=oid), key=lambda t: (rank[_channel_for(t)], t.id))
        chosen = [t.id for t in pool[:room]]
        for i in chosen:
            research_company_task.delay(i)
        ids.extend(chosen)
    return ids
