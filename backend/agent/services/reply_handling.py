from decouple import config as env_config
from anthropic import Anthropic
from .interfaces import DraftOutput
from .research import _extract_json, _estimate_cost

client = Anthropic(api_key=env_config("ANTHROPIC_API_KEY"), timeout=30.0)

CLASSIFY_SYSTEM_PROMPT = """You are classifying an email reply in a business outreach conversation.
Classify it as exactly one of: "interested", "not_interested", "question", "out_of_office".
Respond with ONLY a JSON object: {"classification": string}"""


def classify_reply(thread) -> str:
    from agent.models import AgentInvocation

    history = "\n---\n".join(
        f"[{m.direction}] {m.body}" for m in thread.messages.order_by("created_at")
    )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        system=CLASSIFY_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": history}],
    )
    raw_text = "\n".join(b.text for b in response.content if b.type == "text")
    data = _extract_json(raw_text)
    classification = data["classification"]

    AgentInvocation.objects.create(
        prompt_key="classify_reply",
        input_payload={"thread_id": thread.id},
        output_payload=data,
        model_used="claude-sonnet-4-6",
        tokens_in=response.usage.input_tokens,
        tokens_out=response.usage.output_tokens,
        cost_usd=_estimate_cost(response.usage.input_tokens, response.usage.output_tokens),
    )

    thread.classification = classification
    thread.save()
    return classification


def draft_reply(thread) -> DraftOutput:
    from agent.models import AgentInvocation
    from brain.models import CompanyProfile, Service, Product, SalesRule

    company = CompanyProfile.objects.first()
    services = Service.objects.filter(company=company).values_list("name", flat=True) if company else []
    products = Product.objects.filter(company=company).values_list("name", flat=True) if company else []
    sales_rules = SalesRule.objects.filter(company=company).values_list("rule_text", flat=True) if company else []

    history = "\n---\n".join(
        f"[{m.direction}] {m.body}" for m in thread.messages.order_by("created_at")
    )

    system_prompt = (
        f"You are continuing an email conversation on behalf of {company.name if company else 'KoahCloud'}.\n"
        f"Services: {', '.join(services)}\n"
        f"Products: {', '.join(products)}\n"
        f"Sales rules: {'; '.join(sales_rules)}\n"
        'Keep the reply under 120 words. Answer only what was asked. Never state prices, discounts, deadlines or features that are not listed above; if asked, offer a short call instead.\n'
        'Respond with ONLY a JSON object: {"subject": string, "body": string, "pitch_angle": string}'
    )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": f"Conversation so far:\n{history}"}],
    )
    raw_text = "\n".join(b.text for b in response.content if b.type == "text")
    data = _extract_json(raw_text)

    AgentInvocation.objects.create(
        prompt_key="draft_reply",
        input_payload={"thread_id": thread.id},
        output_payload=data,
        model_used="claude-sonnet-4-6",
        tokens_in=response.usage.input_tokens,
        tokens_out=response.usage.output_tokens,
        cost_usd=_estimate_cost(response.usage.input_tokens, response.usage.output_tokens),
    )

    return DraftOutput(
        subject=data["subject"],
        body=data["body"],
        pitch_angle=data.get("pitch_angle", thread.pitch_angle),
    )
