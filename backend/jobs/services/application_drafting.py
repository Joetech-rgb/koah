from decouple import config as env_config
import re
import requests
from anthropic import Anthropic

ANTHROPIC_API_KEY = env_config("ANTHROPIC_API_KEY", default="")


def _fetch_page_text(url, limit=3000):
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
    except Exception:
        return ""
    t = re.sub(r"(?is)<(script|style|noscript).*?</\1>", " ", r.text)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t).strip()[:limit]


def draft_talking_points(profile, listing) -> str:
    client = Anthropic(api_key=ANTHROPIC_API_KEY)

    skills_list = ", ".join(s.name for s in profile.skills.all()) or "not specified"
    experience_list = "; ".join(
        f"{e.role} at {e.company}" for e in profile.experiences.all()
    ) or "not specified"

    system_prompt = (
        "You write short, honest talking points a candidate can paste into a job "
        "application form. Never fabricate experience the candidate doesn't have. "
        "Keep it to 4-6 bullet points, concrete and specific to the listing. "
        "If the search category is a gig/microtask or AI-training platform, frame the points around signing up, passing assessments and quality of work. "
        "If it is an internship, frame them around learning ability and relevant projects. "
        "If the page excerpt suggests the role is restricted to a region that excludes Ghana, say so in one line at the top."
    )

    page_text = _fetch_page_text(listing.source_url)
    cfg = listing.config
    user_prompt = f"""
Candidate summary: {profile.summary or "not provided"}
Years of experience: {profile.years_experience}
Skills: {skills_list}
Past roles: {experience_list}

Job listing title: {listing.title}
Job listing snippet: {listing.snippet}
Company: {listing.company_name or 'unknown'}
Search category: {cfg.get_category_display()}
Search region: {cfg.region}
Page excerpt: {page_text or 'not available'}

Write talking points connecting this candidate's real background to this specific listing.
"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return response.content[0].text
