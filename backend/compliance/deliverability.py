import dns.resolver


def check_domain_dns(domain: str) -> dict:
    result = {"spf": False, "dkim": False, "dmarc": False}

    try:
        answers = dns.resolver.resolve(domain, "TXT")
        for rdata in answers:
            txt = "".join(s.decode() if isinstance(s, bytes) else s for s in rdata.strings)
            if txt.startswith("v=spf1"):
                result["spf"] = True
    except Exception:
        pass

    try:
        answers = dns.resolver.resolve(f"_dmarc.{domain}", "TXT")
        for rdata in answers:
            txt = "".join(s.decode() if isinstance(s, bytes) else s for s in rdata.strings)
            if txt.startswith("v=DMARC1"):
                result["dmarc"] = True
    except Exception:
        pass

    try:
        answers = dns.resolver.resolve(f"default._domainkey.{domain}", "TXT")
        if answers:
            result["dkim"] = True
    except Exception:
        pass

    return result
