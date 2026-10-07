"""URL health check for a lead's website. Used by audit.py (and re-run there automatically).

check() returns {status, http_code, final_url, note, name_match} where status is:
  ok          page loads (name_match says whether the restaurant's name appears on it)
  parked      loads but is a parked / for-sale / suspended / placeholder page
  blocked     403/429/etc.: bot protection, can't be verified automatically (check by hand)
  dead        domain does not resolve, or HTTP 404/410 on every variant
  unreachable 5xx, timeouts, connection errors (may be temporary; rechecked on the next audit run)

It tries URL variants (www on/off, http<->https, site root) so a bad OSM tag like "www.foo.co"
or a stale deep link is not mistaken for a dead site.
"""
import re
import time
from urllib.parse import urlparse, urlunparse

import httpx

from leadgen import config
from leadgen import store

PARKED = re.compile(
    r"(domain (name )?(is )?(for sale|available)|dominio (est[aá] )?(en venta|disponible)|buy this domain|"
    r"parked (free|domain|by)|account suspended|cuenta suspendida|sitio en construcci[oó]n|"
    r"website (is )?under construction|default web ?site page|index of /|this domain is not configured)", re.I)
PARKING_HOSTS = ("godaddy.com", "sedoparking", "hugedomains", "dan.com", "bodis.com", "parkingcrew", "afternic")
BLOCK_SIGNS = ("cloudflare", "captcha", "access denied", "attention required", "just a moment", "akamai")
DNS_ERRORS = ("getaddrinfo", "name or service", "nodename", "no address associated")
STOPWORDS = {"restaurante", "restaurant", "resto", "cafe", "cafeteria", "bar", "grill", "comida", "pizzeria",
             "the", "los", "las", "del", "de", "la", "el", "y", "and"}


def init(con):
    con.execute(
        """CREATE TABLE IF NOT EXISTS url_checks (
            place_id TEXT PRIMARY KEY, url TEXT, status TEXT, http_code INTEGER,
            final_url TEXT, note TEXT, name_match INTEGER, checked_at REAL)""")


def save(con, place_id, url, res):
    con.execute("INSERT OR REPLACE INTO url_checks VALUES (?,?,?,?,?,?,?,?)",
                (place_id, url, res["status"], res.get("http_code"), res.get("final_url"),
                 res.get("note"), res.get("name_match"), time.time()))
    con.commit()


def candidates(url):
    """Original first, then likely fixes. Yields (url, host)."""
    u = urlparse(url)
    host = u.netloc.lower()
    alt_host = host[4:] if host.startswith("www.") else "www." + host
    out = [url, urlunparse(u._replace(netloc=alt_host)),
           urlunparse(u._replace(scheme="https" if u.scheme == "http" else "http"))]
    if u.path not in ("", "/"):
        out.append(urlunparse(u._replace(path="/", params="", query="", fragment="")))
    return list(dict.fromkeys(out))


def _get(client, url):
    """-> (response or None, kind) with kind in resp/dns/timeout/conn. Retries once on transient errors."""
    kind = "conn"
    for attempt in range(2):
        try:
            return client.get(url, timeout=15, follow_redirects=True, headers={"User-Agent": config.BROWSER_UA}), "resp"
        except httpx.TimeoutException:
            kind = "timeout"
        except httpx.ConnectError as e:
            if any(s in str(e).lower() for s in DNS_ERRORS):
                return None, "dns"
            kind = "conn"
        except Exception:
            kind = "conn"
        time.sleep(2)
    return None, kind


def _tokens(name):
    return [t for t in store._norm(name).split() if len(t) >= 4 and t not in STOPWORDS]


def _digits(s):
    return re.sub(r"\D", "", s or "")


def match_place(host, text, name, phone=""):
    """Does this page belong to the restaurant? -> (name_match, phone_match, locality, note).
    name_match: 1 verified, 0 name absent (probably another business), None cannot tell.
    A single shared word among several name words is not enough on its own: it needs the phone or a local mention."""
    toks = _tokens(name)
    page = store._norm(text)
    hay = host.lower() + " " + page
    ph = _digits(phone)[-7:]
    phone_match = len(ph) == 7 and ph in _digits(text)
    locality = any(w in page for w in config.LOCALITY_WORDS)
    hits = [t for t in toks if t in hay]
    in_host = any(t in host.lower().replace("-", "") for t in toks)
    if phone_match or (in_host and len(toks) <= 1):
        match = 1
    elif not toks:
        match = None
    elif not hits:
        match = 0
    elif len(toks) == 1 or len(hits) >= 2 or in_host:
        match = 1
    else:
        match = 1 if locality else None    # one word of several: only trust it when the page is local
    note = "" if match != 0 else "restaurant name not found on the page (may be the wrong site)"
    if match is None:
        note = "only part of the restaurant name found on the page (unverified)"
    return match, phone_match, locality, note


def _classify_ok(r, name, phone=""):
    final = str(r.url)
    host = urlparse(final).netloc.lower()
    text = r.text[:60000]
    if any(h in host for h in PARKING_HOSTS) or PARKED.search(text[:30000]):
        return {"status": "parked", "http_code": r.status_code, "final_url": final,
                "note": "parked / placeholder page", "name_match": None}
    match, phone_match, locality, note = match_place(host, re.sub(r"<[^>]+>", " ", text), name, phone)
    return {"status": "ok", "http_code": r.status_code, "final_url": final, "note": note, "name_match": match,
            "phone_match": phone_match, "locality": locality, "response": r}


def check(client, url, name="", phone=""):
    """`phone` (the place's listed number) only strengthens the wrong-site check. The returned dict for an `ok`
    page also carries `response`, so the caller can audit the page without fetching it a second time."""
    tried = []                       # (response|None, kind)
    dead_hosts = set()
    for cand in candidates(url):
        host = urlparse(cand).netloc
        if host in dead_hosts:
            continue
        r, kind = _get(client, cand)
        if r is not None and r.status_code < 400:
            return _classify_ok(r, name, phone)
        if kind == "dns":
            dead_hosts.add(host)
        tried.append((r, kind))

    codes = [r.status_code for r, _ in tried if r is not None]
    base = {"final_url": url, "name_match": None}
    blocked = [r for r, _ in tried if r is not None and (
        r.status_code in (401, 403, 429) or (r.status_code in (503, 520) and any(s in r.text[:5000].lower() for s in BLOCK_SIGNS)))]
    if blocked:
        return {**base, "status": "blocked", "http_code": blocked[0].status_code,
                "note": f"HTTP {blocked[0].status_code}: likely bot protection, verify by hand"}
    if all(k == "dns" for _, k in tried):
        return {**base, "status": "dead", "http_code": None, "note": "domain does not resolve"}
    gone = [c for c in codes if c in (404, 410)]
    if gone:
        return {**base, "status": "dead", "http_code": gone[0], "note": f"page not found (HTTP {gone[0]})"}
    if codes:
        return {**base, "status": "unreachable", "http_code": codes[0], "note": f"server error (HTTP {codes[0]})"}
    return {**base, "status": "unreachable", "http_code": None, "note": "no response (timeout / connection error)"}
