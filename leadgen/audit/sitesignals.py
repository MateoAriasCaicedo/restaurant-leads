"""Read a fetched page into the signals audit.py scores.

Looks at links, headings, the <head> and the visible text rather than raw substrings of the HTML, so words
inside scripts, CSS and JSON bundles no longer count. A signal that cannot be judged (a JavaScript-rendered
page whose body is empty in the raw HTML) is None, not 0: web_score() leaves it out instead of penalising it.
"""
import json
import re

from bs4 import BeautifulSoup

MENU = re.compile(r"\b(men[uú]s?|carta|nuestros platos|platos)\b", re.I)
RESERVE = re.compile(r"(reserv|book a table|agendar|opentable|resy\.com)", re.I)
ORDER = re.compile(r"(\bpedir\b|pide ya|pide aqu|domicilio|order online|ordena ya|rappi|ifood|didi ?food|ubereats|uber eats)", re.I)
WA_HOSTS = ("wa.me", "api.whatsapp.com", "web.whatsapp.com", "wa.link", "whatsapp://")
WA_WIDGET = re.compile(r"(whatsapp|joinchat|qlwapp|getbutton\.io)", re.I)
WA_NUMBER = re.compile(r"whatsapp[^0-9]{0,20}(?:\+?57)?[\s-]?3\d{2}", re.I)
COPYRIGHT = re.compile(r"(?:©|copyright|derechos reservados)[^0-9]{0,40}((?:19|20)\d{2})(?:\s*[-–]\s*((?:19|20)\d{2}))?", re.I)
SHELL_MARKERS = ('id="root"', "id='root'", 'id="app"', 'id="__next"', 'id="__nuxt"', "ng-app", "data-reactroot")
SHELL_MAX_TEXT = 300      # fewer visible characters than this, plus scripts, = body rendered by JavaScript


def _schema_ok(soup):
    for tag in soup.find_all("script", type=re.compile(r"ld\+json", re.I)):
        try:
            data = json.loads(tag.string or tag.get_text() or "")
        except ValueError:
            continue
        if data:
            return 1
    return 0


def parse(html):
    soup = BeautifulSoup(html, "html.parser")
    raw_low = html.lower()
    scripts = soup.find_all("script")

    head = {}
    for m in soup.find_all("meta"):
        key = (m.get("name") or m.get("property") or "").lower()
        if key and key not in head:
            head[key] = (m.get("content") or "").strip()

    links = [((a.get("href") or "").strip(), a.get_text(" ", strip=True)) for a in soup.find_all("a")]
    buttons = [b.get_text(" ", strip=True) for b in soup.find_all("button")]
    headings = [h.get_text(" ", strip=True) for h in soup.find_all(["h1", "h2", "h3"])]
    pdfs = [h for h, _ in links if h.lower().split("?")[0].endswith(".pdf")]

    scrap = BeautifulSoup(html, "html.parser")
    for t in scrap(["script", "style", "noscript", "template"]):
        t.decompose()
    text = scrap.get_text(" ", strip=True)
    hay = " ".join([text] + [h + " " + t for h, t in links] + buttons)

    shell = len(text) < SHELL_MAX_TEXT and (len(scripts) >= 2 or any(m in raw_low for m in SHELL_MARKERS))

    menu = int(bool(MENU.search(" ".join(headings + [t for _, t in links] + [h for h, _ in links] + buttons
                                         + [soup.title.get_text(" ", strip=True) if soup.title else ""]))))
    wa = int(any(any(w in h.lower() for w in WA_HOSTS) for h, _ in links)
             or bool(WA_NUMBER.search(text))
             or any(WA_WIDGET.search(s.get("src") or "") for s in scripts)
             or soup.find(class_=WA_WIDGET) is not None)
    tel = int(any(h.lower().startswith("tel:") for h, _ in links))

    years = []
    for m in COPYRIGHT.finditer(text):
        years += [int(g) for g in m.groups() if g]

    out = {
        "viewport": int("viewport" in head),
        "has_title": int(bool(soup.title and soup.title.get_text(strip=True))),
        "has_meta_desc": int(bool(head.get("description"))),
        "has_h1": int(soup.find("h1") is not None),
        "has_menu_text": menu,
        "menu_pdf_only": int(bool(pdfs) and not menu),
        "has_whatsapp": wa,
        "has_tel": tel,
        "has_reserve": int(bool(RESERVE.search(hay))),
        "has_order": int(bool(ORDER.search(hay))),
        "has_schema": _schema_ok(soup),
        "copyright_year": max(years) if years else None,
        "js_shell": int(shell),
    }
    if shell:
        # the body is built by JavaScript: absence of these in the raw HTML proves nothing
        for k in ("has_h1", "has_menu_text", "menu_pdf_only", "has_tel", "has_reserve", "has_order"):
            out[k] = None
        if not wa:
            out["has_whatsapp"] = None
    return out
