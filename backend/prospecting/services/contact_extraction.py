import re
import requests
from bs4 import BeautifulSoup

EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_PATTERN = re.compile(r"(\+?\d{1,3}[\s.-]?)?(\(?\d{2,4}\)?[\s.-]?){2,4}\d{2,4}")

CANDIDATE_PATHS = ["", "/contact", "/contact-us", "/about", "/about-us"]


def extract_contact_phone(domain: str) -> str | None:
    if not domain:
        return None

    for path in CANDIDATE_PATHS:
        url = f"https://{domain}{path}"
        try:
            response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            if response.status_code != 200:
                continue
        except requests.RequestException:
            continue

        soup = BeautifulSoup(response.text, "html.parser")

        for link in soup.find_all("a", href=True):
            if link["href"].startswith("tel:"):
                phone = link["href"].replace("tel:", "").strip()
                if len(re.sub(r"\D", "", phone)) >= 7:
                    return phone

        match = PHONE_PATTERN.search(soup.get_text())
        if match and len(re.sub(r"\D", "", match.group(0))) >= 7:
            return match.group(0).strip()

    return None


def extract_contact_email(domain: str) -> str | None:
    if not domain:
        return None

    for path in CANDIDATE_PATHS:
        url = f"https://{domain}{path}"
        try:
            response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            if response.status_code != 200:
                continue
        except requests.RequestException:
            continue

        soup = BeautifulSoup(response.text, "html.parser")

        for link in soup.find_all("a", href=True):
            if link["href"].startswith("mailto:"):
                email = link["href"].replace("mailto:", "").split("?")[0].strip()
                if EMAIL_PATTERN.match(email):
                    return email

        match = EMAIL_PATTERN.search(soup.get_text())
        if match:
            return match.group(0)

    return None
