import json
import time
from decouple import config as env_config
from anthropic import Anthropic
from .interfaces import ResearchInput, ResearchOutput

client = Anthropic(api_key=env_config("ANTHROPIC_API_KEY"), timeout=30.0)

RESEARCH_SYSTEM_PROMPT = """You are a business research assistant. Given a company name (it may include the organization type, address or Facebook page in brackets), a domain (which may be unknown), and country, use web search to determine:
1. Whether the company has a live website (has_website: bool)
2. Their industry (detected_industry: string)
3. Any software/tools visibly in use on their site (detected_tools: list of strings)
4. A 2-3 sentence summary of what the company does (summary: string)
5. Your confidence in this research, 0.0-1.0 (confidence: float)

If the domain is unknown, search for the organization by name and location. If you cannot find a real website for it, set has_website to false. Never invent details you did not find.

Respond with ONLY a JSON object matching this exact schema, no other text:
{"has_website": bool, "detected_industry": string, "detected_tools": [string], "summary": string, "confidence": float}"""


def _extract_json(text: str) -> dict:
    text = text.strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise json.JSONDecodeError("no JSON object found", text, 0)
    return json.loads(text[start:end + 1])


def _estimate_cost(tokens_in: int, tokens_out: int) -> float:
    return round((tokens_in / 1_000_000) * 3 + (tokens_out / 1_000_000) * 15, 6)


def research_company(input: ResearchInput) -> ResearchOutput:
    from agent.models import AgentInvocation

    user_prompt = f"Company: {input.company_name}\nDomain: {input.domain or 'unknown'}\nCountry: {input.country or 'unknown'}"
    input_payload = {"company_name": input.company_name, "domain": input.domain, "country": input.country}
    start = time.monotonic()

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=RESEARCH_SYSTEM_PROMPT,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw_text = "\n".join(b.text for b in response.content if b.type == "text")

        try:
            data = _extract_json(raw_text)
        except (json.JSONDecodeError, IndexError):
            retry_prompt = user_prompt + f"\n\nYour previous response could not be parsed as JSON: {raw_text}\nRespond again with ONLY valid JSON matching the schema."
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                system=RESEARCH_SYSTEM_PROMPT,
                tools=[{"type": "web_search_20250305", "name": "web_search"}],
                messages=[{"role": "user", "content": retry_prompt}],
            )
            raw_text = "\n".join(b.text for b in response.content if b.type == "text")
            data = _extract_json(raw_text)

        output = ResearchOutput(
            has_website=data["has_website"],
            detected_industry=data["detected_industry"],
            detected_tools=data.get("detected_tools", []),
            summary=data["summary"],
            confidence=float(data.get("confidence", 0.5)),
        )

        AgentInvocation.objects.create(
            prompt_key="research_company",
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
            prompt_key="research_company",
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
