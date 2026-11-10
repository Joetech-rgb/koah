import time
from decouple import config as env_config
from anthropic import Anthropic
from .interfaces import DraftInput, DraftOutput
from .research import _extract_json, _estimate_cost

client = Anthropic(api_key=env_config("ANTHROPIC_API_KEY"), timeout=30.0)


def _determine_pitch_angle(research, prospect=None) -> str:
    status = (prospect or {}).get("website_status")
    if status == "none":
        return "website"
    if status == "social_only":
        return "website_social"
    if status == "has_website":
        return "software"
    return "website" if not research.has_website else "software"


ANGLE_GUIDE = {
    "website": "This organization has NO website; customers only find it through a Google listing or word of mouth. Lead with a professional website plus Google Business/SEO setup, then connect one more relevant offer.",
    "website_social": "This organization only has social media pages (Facebook, Instagram or similar), no website. Lead with a proper website plus automating repetitive work (orders, bookings, customer messages), then connect one more relevant offer.",
    "software": "This organization already has a website. Do not pitch a basic website. Lead with the offer from the catalog that best fits what this type of organization needs (AI automation, custom software, POS, management system, SEO or redesign).",
}


CHANNEL_GUIDE = {
    "email": "Channel: email. Write a normal short email.",
    "phone": "Channel: WhatsApp/SMS message (we only have a phone number). This overrides the length rule above: write the body as a short, friendly message under 60 words, no formal letter format, and set subject to a short label. Do not mention email.",
    "facebook": "Channel: Facebook Messenger message to their page. This overrides the length rule above: write the body as a short, friendly message under 70 words, no formal letter format, and set subject to a short label.",
    "social": "Channel: direct message on their social media profile. This overrides the length rule above: write the body as a short, casual message under 60 words and set subject to a short label.",
    "none": "Channel: unknown. Write a short generic email draft.",
}


GENERIC_ANGLE_GUIDE = {
    "website": "This organization has no website of its own; customers find it through a Google listing or word of mouth. Choose the offer from the catalog that best fits what this type of organization needs.",
    "website_social": "This organization only has social media pages, no website. Choose the offer from the catalog that best fits what this type of organization needs.",
    "software": "This organization already has a website. Choose the offer from the catalog that best fits what this type of organization needs.",
}


def _build_system_prompt(brain_context: dict, pitch_angle: str, country: str = None) -> str:
    company = brain_context.get("company", {})
    services = brain_context.get("services", [])
    products = brain_context.get("products", [])
    sales_rules = brain_context.get("sales_rules", [])
    prospect = brain_context.get("prospect", {}) or {}
    catalog = brain_context.get("catalog", []) or []
    tone = company.get("email_tone", "professional and warm")

    lines = [
        f"You are writing a cold outreach email on behalf of {company.get('name', 'KoahCloud')}.",
        f"Company description: {company.get('description', '')}",
        f"Tone: {tone}",
        f"Services offered: {', '.join(s['name'] for s in services)}",
        f"Products offered: {', '.join(p['name'] for p in products)}",
        "Sales rules to follow strictly:",
    ]
    for rule in sales_rules:
        lines.append(f"- {rule}")

    lines.append(f"Recipient: {prospect.get('name') or 'the organization'} ({prospect.get('org_type') or 'organization'}).")
    if prospect.get("address"):
        lines.append(f"Location: {prospect['address']}")
    lines.append((GENERIC_ANGLE_GUIDE if prospect.get("generic_angle") else ANGLE_GUIDE).get(pitch_angle, ANGLE_GUIDE["software"]))

    if prospect.get("playbook"):
        lines.append(f"What this type of organization typically needs: {prospect['playbook']}")

    if catalog:
        lines.append("Our full catalog. Pitch ONLY things from this list, never invent services:")
        for item in catalog:
            lines.append(f"- {item['offer']} (suits: {item['fits']})")
        lines.append("Choose ONE primary offer that best fits this type of organization, plus at most one secondary offer." + ("" if prospect.get("generic_angle") else " If IT hardware (laptops, routers, networking) genuinely fits, it may be the secondary line."))

    lines.append("Keep the email under 150 words, specific to this type of organization, with one clear call to action. Do not claim to have seen details about them that you were not given.")

    phone = company.get("phone")
    if phone:
        lines.append(f"End the email with a signature including this phone number: {phone}")

    _home = (company.get("based_in") or "Ghana")
    if country and _home.lower() not in country.lower():
        lines.append(f"The recipient is outside {_home} - introduce the company as a {_home}-based provider.")

    lines.append(CHANNEL_GUIDE.get(prospect.get("channel"), CHANNEL_GUIDE["email"]))
    lines.append('Respond with ONLY a JSON object: {"subject": string, "body": string, "pitch_angle": string (short label of the primary offer, max 30 characters)}')
    return "\n".join(lines)


def draft_pitch(input: DraftInput) -> DraftOutput:
    from agent.models import AgentInvocation

    pitch_angle = _determine_pitch_angle(input.research, input.brain_context.get("prospect"))
    system_prompt = _build_system_prompt(input.brain_context, pitch_angle, input.brain_context.get("country"))
    input_payload = {"research_summary": input.research.summary, "pitch_angle": pitch_angle}
    start = time.monotonic()

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": f"Research summary: {input.research.summary}\nDetected industry: {input.research.detected_industry}\nTools seen on their site: {', '.join(input.research.detected_tools or []) or 'none detected'}"}],
        )
        raw_text = "\n".join(b.text for b in response.content if b.type == "text")
        data = _extract_json(raw_text)

        output = DraftOutput(
            subject=data["subject"],
            body=data["body"],
            pitch_angle=str(data.get("pitch_angle", pitch_angle))[:40],
        )

        AgentInvocation.objects.create(
            prompt_key="draft_pitch",
            input_payload=input_payload,
            output_payload=data,
            model_used="claude-sonnet-4-6",
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
            cost_usd=_estimate_cost(response.usage.input_tokens, response.usage.output_tokens),
            status="success",
            duration_ms=int((time.monotonic() - start) * 1000),
        )
        return output

    except Exception as e:
        AgentInvocation.objects.create(
            prompt_key="draft_pitch",
            input_payload=input_payload,
            output_payload={"error": str(e)},
            model_used="claude-sonnet-4-6",
            tokens_in=0,
            tokens_out=0,
            cost_usd=0,
            status="failed",
            duration_ms=int((time.monotonic() - start) * 1000),
        )
        raise
