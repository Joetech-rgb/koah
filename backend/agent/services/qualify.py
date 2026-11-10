import time
from decouple import config as env_config
from anthropic import Anthropic
from .research import _extract_json, _estimate_cost

MODEL = "claude-haiku-5-5"

SYSTEM = """You screen prospects for a Ghana-based software agency. Given a record found by search, decide whether it looks like ONE real, operating small or mid-sized business or organization that matches the target niche and region.
Reject (real_business=false) ONLY when you are fairly confident it is one of: a directory or listing site, an article or guide, a job or classified ad, a government body or regulator, a major multinational, the personal profile of an individual, a business in a clearly different country than the target region, or clearly not in the niche.
If unsure, or the name simply looks small or unfamiliar, answer true.
Respond with ONLY JSON: {"real_business": bool, "reason": string (max 12 words)}"""


def qualify_company(tc):
    """Returns (ok, reason). Fails open: any error lets the company through."""
    from agent.models import AgentInvocation
    niche = tc.source_niche
    user = (
        f"Name: {tc.name}\n"
        f"Domain: {tc.domain or 'none'}\n"
        f"Website status: {tc.website_status}\n"
        f"Found via: {tc.discovery_source}\n"
        f"Category: {tc.org_type}\n"
        f"Address: {tc.contact_address or 'unknown'}\n"
        f"Target niche: {niche.niche_name if niche else 'unknown'}\n"
        f"Target region: {niche.region if niche else tc.country}"
    )
    payload = {"company_id": tc.id, "name": tc.name}
    start = time.monotonic()
    try:
        client = Anthropic(api_key=env_config("ANTHROPIC_API_KEY", default=""), timeout=20.0)
        r = client.messages.create(model=MODEL, max_tokens=120, system=SYSTEM,
                                   messages=[{"role": "user", "content": user}])
        data = _extract_json("\n".join(b.text for b in r.content if b.type == "text"))
        ok = bool(data.get("real_business", True))
        reason = str(data.get("reason", ""))[:200]
        AgentInvocation.objects.create(
            prompt_key="qualify", input_payload=payload, output_payload=data, model_used=MODEL,
            tokens_in=r.usage.input_tokens, tokens_out=r.usage.output_tokens,
            cost_usd=_estimate_cost(r.usage.input_tokens, r.usage.output_tokens),
            status="success", duration_ms=int((time.monotonic() - start) * 1000))
        return ok, reason
    except Exception as e:
        try:
            AgentInvocation.objects.create(
                prompt_key="qualify", input_payload=payload, output_payload={"error": str(e)}, model_used=MODEL,
                tokens_in=0, tokens_out=0, cost_usd=0, status="failed",
                duration_ms=int((time.monotonic() - start) * 1000))
        except Exception:
            pass
        return True, "check skipped: " + str(e)[:80]
