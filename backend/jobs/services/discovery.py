import re
import requests
from decouple import config as env_config

SERPER_API_KEY = env_config("SERPER_API_KEY", default="")
SERPER_URL = "https://google.serper.dev/search"
MAILTO_PATTERN = re.compile(r"mailto:([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})")


REGION_GL = {
    "ghana": "gh", "accra": "gh", "kumasi": "gh",
    "uk": "gb", "london": "gb", "united kingdom": "gb", "england": "gb",
    "nigeria": "ng", "lagos": "ng", "kenya": "ke", "nairobi": "ke",
    "south africa": "za", "mauritius": "mu", "canada": "ca",
    "usa": "us", "united states": "us", "india": "in", "germany": "de",
    "uae": "ae", "dubai": "ae",
}


def _geo(region: str) -> dict:
    r = (region or "").lower()
    for key, gl in REGION_GL.items():
        if re.search(r"\b" + re.escape(key) + r"\b", r):
            return {"gl": gl}
    return {}


INELIGIBLE = (
    "us only", "u.s. only", "usa only", "united states only", "us citizens only", "u.s. citizens only",
    "must reside in the us", "must be located in the us", "must be based in the us",
    "uk only", "eu only", "europe only", "canada only",
)


def _guess_company(title):
    m = re.search(r"\bat\s+([A-Z][^|\-\u2013]{1,60})", title or "")
    return m.group(1).strip() if m else ""


def _is_listing_page(title):
    t = (title or "").lower()
    if re.match(r"^\d[\d,\+]*\s", t) and "job" in t:
        return True
    return "jobs in" in t and " at " not in t


def find_jobs(role_query: str, region: str) -> list[dict]:
    query = f"{role_query} jobs {region}"

    response = requests.post(
        SERPER_URL,
        headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
        json={"q": query, "num": 10, **_geo(region)},
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()

    region_l = (region or "").lower()
    strict = "africa" in region_l or "ghana" in region_l
    listings = []
    for item in data.get("organic", []):
        title = item.get("title", "").strip()
        snippet = item.get("snippet", "")
        if _is_listing_page(title):
            continue
        blob = (title + " " + snippet).lower()
        if strict and any(p in blob for p in INELIGIBLE):
            continue
        listings.append({
            "title": title,
            "company_name": _guess_company(title),
            "source_url": item.get("link", ""),
            "snippet": snippet,
        })
    return listings


def extract_email_from_url(url: str) -> str | None:
    try:
        response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
    except Exception:
        return None

    match = MAILTO_PATTERN.search(response.text)
    if match:
        return match.group(1)
    return None
