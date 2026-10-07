"""Look for the website of a place that OpenStreetMap lists without one.

No search engine is scraped: candidate domains are derived from the restaurant's name (elputotaco.com,
el-putotaco.com.co, ...), only hosts that resolve in DNS are fetched, and a page is accepted only when it is
clearly the same business: the listed phone number is on it, or its name matches and it mentions the
locality. Anything weaker is dropped, so a miss costs nothing and a false match is rare.
"""
import socket
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

from leadgen import config
from leadgen import store
from leadgen.audit import urlcheck

def slugs(name):
    toks = store._norm(name).split()
    no_generic = [t for t in toks if t not in {"restaurante", "restaurant", "resto"}]
    core = [t for t in toks if t not in urlcheck.STOPWORDS]
    # Branch names carry the neighbourhood ("Naan Laureles"), but the brand's domain rarely does.
    areas = {t for k in config.ALL_AREAS for t in k.split("_")}
    brand = [t for t in core if t not in areas]
    out = ["".join(no_generic), "-".join(no_generic), "".join(core), "".join(toks), "".join(brand), "-".join(brand)]
    return [s for s in dict.fromkeys(out) if len(s.replace("-", "")) >= 4]


def hosts(name):
    return [f"{s}.{tld}" for s in slugs(name) for tld in config.DISCOVER_TLDS]


def resolves(host):
    try:
        socket.getaddrinfo(host, 443)
        return True
    except OSError:
        return False


def find(client, name, phone=""):
    """-> (url, evidence) for a verified site, or (None, note)."""
    cands = hosts(name)
    if not cands:
        return None, "name too short to guess a domain"
    with ThreadPoolExecutor(max_workers=12) as ex:
        live = [h for h, ok in zip(cands, ex.map(resolves, cands)) if ok]
    if not live:
        return None, f"no domain resolved ({len(cands)} guesses)"
    for host in live:
        res = urlcheck.check(client, "https://" + host, name, phone)
        if res["status"] != "ok" or res.get("name_match") != 1:
            continue
        final_host = urlparse(res["final_url"]).netloc.lower().replace("www.", "")
        if any(final_host == d or final_host.endswith("." + d) for d in config.SOCIAL_DOMAINS):
            continue                                 # redirects to a social page: not a website of their own
        if res.get("phone_match"):
            return res, f"found {host}: the listed phone number is on the page"
        if res.get("locality"):
            return res, f"found {host}: name matches and the page mentions the area"
    return None, f"{len(live)} guessed domain(s) resolved but none matched the business"
