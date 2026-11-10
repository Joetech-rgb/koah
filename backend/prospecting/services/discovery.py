import re
import requests
from urllib.parse import urlparse
from decouple import config as env_config

SERPER_API_KEY = env_config("SERPER_API_KEY", default="")
SERPER_URL = "https://google.serper.dev/search"
SERPER_PLACES_URL = "https://google.serper.dev/places"

MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
PHONE_IN_TEXT = re.compile(r"\+?\d[\d\s().-]{7,}\d")

BLOCKED_DOMAINS = {
    "techbehemoths.com", "themanifest.com", "ensun.io", "clutch.co",
    "websysgh.com", "dnb.com", "yelp.com", "yellowpages.com",
    "goodfirms.co", "designrush.com", "upcity.com", "sortlist.com",
    "africabizinfo.com", "worldplaces.me", "cybo.com", "absa.com.gh", "ubaghana.com", "ubagroup.com",
    "totalenergies.com.gh", "epaoilandgas.org", "gepaghana.org",
    "africa2trust.com", "nigeriabusinessweb.com", "ghanabusinessweb.com", "businessghana.com",
    "bizseek.co.uk",
    "carfax.com", "autotrader.com", "cars.com", "cargurus.com", "alibaba.com", "tripadvisor", "ebay.com", "amazon.com",
    "ngex.com", "nigeria24.me", "businesslist", "vconnect", "ghanayello", "finelib", "cylex", "brabys",
    "thomsonlocal", ".gov.uk", ".gov.gh", "yell.com", "checkatrade", "trustpilot", "reddit.com", "quora.com",
}
SOCIAL_DOMAINS = ("facebook.com", "fb.com", "instagram.com")
FB_SKIP_SEGMENTS = {"posts", "groups", "events", "public", "login", "watch", "photo", "photos", "videos", "reel", "share", "sharer", "marketplace", "hashtag", "story.php", "permalink.php"}


def _clean_url(raw: str) -> str:
    if not raw:
        return raw
    match = MARKDOWN_LINK_PATTERN.match(raw.strip())
    if match:
        return match.group(2)
    return raw


def _host(url: str):
    if not url:
        return None
    if "//" not in url:
        url = "https://" + url
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else (host or None)


def normalize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (name or "").lower())


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


def _post(url, payload):
    response = requests.post(
        url,
        headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
        json=payload,
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def _facebook_page_url(link: str):
    """Return a clean facebook page URL, or None if it's a post/group/etc."""
    p = urlparse(link if "//" in link else "https://" + link)
    segs = [s for s in p.path.split("/") if s]
    if not segs or segs[0].lower() in FB_SKIP_SEGMENTS:
        return None
    return f"https://www.facebook.com/{segs[0]}"


def find_businesses(niche: str, region: str) -> list[dict]:
    """Source 1: normal web search (organizations that have websites)."""
    data = _post(SERPER_URL, {"q": f"{niche} company {region} contact -top -best -list -ranked", "num": 10, **_geo(region)})
    candidates = []
    for item in data.get("organic", []):
        link = _clean_url(item.get("link", ""))
        domain = _host(link)
        if not domain or any(b in domain for b in BLOCKED_DOMAINS):
            continue
        if _is_social(domain):
            continue
        candidates.append({
            "name": re.split(r" [-|\u2013\u2014] ", item.get("title", ""))[0].strip(),
            "domain": domain,
            "snippet": item.get("snippet", ""),
            "source": "web",
        })
    return candidates


def find_places(niche: str, region: str) -> list[dict]:
    """Source 2: Google Business profiles (with or without a website)."""
    data = _post(SERPER_PLACES_URL, {"q": f"{niche} in {region}", **_geo(region)})
    candidates = []
    for p in data.get("places", []) or []:
        name = (p.get("title") or p.get("name") or "").strip()
        if not name:
            continue
        website = p.get("website") or p.get("link") or ""
        host = _host(website)
        facebook_url = None
        if host and any(s in host for s in SOCIAL_DOMAINS):
            if "facebook.com" in host or "fb.com" in host:
                facebook_url = _facebook_page_url(website)
            host = None
        if host and any(b in host for b in BLOCKED_DOMAINS):
            host = None
        cid = p.get("cid") or p.get("placeId") or p.get("place_id")
        candidates.append({
            "name": name,
            "domain": host,
            "facebook_url": facebook_url,
            "google_cid": str(cid) if cid else None,
            "phone": p.get("phoneNumber") or p.get("phone") or p.get("phone_number"),
            "address": p.get("address"),
            "category": p.get("category") or p.get("type"),
            "source": "places",
        })
    return candidates


def find_facebook_pages(niche: str, region: str) -> list[dict]:
    """Source 3: public Facebook business pages found through search results."""
    data = _post(SERPER_URL, {"q": f"site:facebook.com {niche} {region}", "num": 10, **_geo(region)})
    candidates = []
    seen = set()
    for item in data.get("organic", []):
        link = _clean_url(item.get("link", ""))
        if "facebook.com" not in (link or ""):
            continue
        page = _facebook_page_url(link)
        if not page or page in seen:
            continue
        seen.add(page)
        title = item.get("title", "")
        name = re.split(r" [-|\u2013\u2022] ", title)[0].strip()
        slug = page.rsplit("/", 1)[-1]
        if slug.isdigit():
            continue
        if name.endswith("...") or "#" in name or len(name) > 60:
            name = re.sub(r"[-_.]+", " ", slug).title()
        snippet = item.get("snippet", "")
        m = PHONE_IN_TEXT.search(snippet)
        phone = m.group(0).strip() if m and len(re.sub(r"\D", "", m.group(0))) >= 9 else None
        if name:
            candidates.append({
                "name": name,
                "domain": None,
                "facebook_url": page,
                "phone": phone,
                "snippet": snippet,
                "source": "facebook",
            })
    return candidates

def _is_social(host):
    host = (host or "").lower()
    return any(host == d or host.endswith("." + d) for d in
               ("facebook.com", "fb.com", "instagram.com", "twitter.com", "x.com",
                "tiktok.com", "linkedin.com", "wa.me", "linktr.ee"))


SOCIAL_SKIP = {
    "instagram": {"p", "reel", "reels", "explore", "tv", "stories", "accounts", "tags", "directory"},
    "x": {"i", "search", "hashtag", "explore", "home", "intent", "share", "login"},
    "tiktok": {"discover", "tag", "video", "music", "search"},
}


def find_social_profiles(niche: str, region: str) -> list[dict]:
    """Source 4: public Instagram / X / TikTok / LinkedIn profiles found through search results."""
    q = ("(site:instagram.com OR site:x.com OR site:twitter.com OR site:tiktok.com "
         "OR site:linkedin.com/company) " + niche + " " + region)
    data = _post(SERPER_URL, {"q": q, "num": 10, **_geo(region)})
    out, seen = [], set()
    for item in data.get("organic", []):
        link = _clean_url(item.get("link", ""))
        host = _host(link)
        if not host:
            continue
        p = urlparse(link if "//" in link else "https://" + link)
        segs = [s for s in p.path.split("/") if s]
        if host.endswith("instagram.com"):
            platform = "instagram"
        elif host == "x.com" or host.endswith("twitter.com"):
            platform = "x"
        elif host.endswith("tiktok.com"):
            platform = "tiktok"
        elif host.endswith("linkedin.com"):
            platform = "linkedin"
        else:
            continue
        if platform == "linkedin":
            if len(segs) < 2 or segs[0] != "company":
                continue
            handle = segs[1]
            url = "https://www.linkedin.com/company/" + handle
        else:
            if not segs:
                continue
            handle = segs[0].lstrip("@")
            if not handle or handle.isdigit() or handle.lower() in SOCIAL_SKIP.get(platform, set()):
                continue
            if platform == "instagram":
                url = "https://www.instagram.com/" + handle
            elif platform == "x":
                url = "https://x.com/" + handle
            else:
                url = "https://www.tiktok.com/@" + handle
        if url in seen:
            continue
        seen.add(url)
        title = item.get("title", "")
        name = re.split(r" \(@| \u2022 | - | \| ", title)[0].strip()
        if not name or name.endswith("...") or "#" in name or len(name) > 60:
            name = re.sub(r"[-_.]+", " ", handle).title()
        snippet = item.get("snippet", "")
        m = PHONE_IN_TEXT.search(snippet)
        phone = m.group(0).strip() if m and len(re.sub(r"\D", "", m.group(0))) >= 9 else None
        out.append({"name": name, "domain": None, "social_url": url, "social_platform": platform,
                    "phone": phone, "snippet": snippet, "source": "social"})
    return out
