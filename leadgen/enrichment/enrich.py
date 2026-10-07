"""Per-lead enrichment: own-site crawl + dropped-in photos -> Claude extraction -> lead profile

Usage: python enrich.py [--only NAME_OR_ID] [--refresh]
Processes leads with status 'approved' (see approve.py). Each stage's result is cached as JSON in
leads/<slug>/profile/, so re-runs only pay for missing stages; --refresh redoes the LLM stages
(downloaded files in raw/ are reused).
"""
import argparse
import hashlib
import json
import re
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from leadgen import config
from leadgen.enrichment import llm
from leadgen.enrichment import research
from leadgen import store

PAGE_HINTS = ("menu", "carta", "nosotros", "about", "quienes", "historia", "contacto", "contact", "galeria", "gallery", "platos", "ubicacion")
SKIP_IMG = ("logo", "icon", "sprite", "favicon", "avatar", "pixel", "tracking", "spinner", "placeholder", "payment")
IMG_EXT = (".jpg", ".jpeg", ".png", ".webp")
GENERIC_FONTS = {"sans-serif", "serif", "monospace", "inherit", "initial", "system-ui", "cursive", "fantasy", "arial", "helvetica", "times new roman"}


def get(client, url):
    try:
        r = client.get(url, timeout=25, follow_redirects=True, headers={"User-Agent": config.USER_AGENT})
        return r if r.status_code < 400 else None
    except Exception:
        return None


def fetch_file(client, url, dest_dir, max_mb, min_kb=0):
    """Download once (filename = hash of URL). Returns Path or None."""
    ext = Path(urlparse(url).path).suffix.lower() or ".bin"
    dest = dest_dir / (hashlib.sha1(url.encode()).hexdigest()[:12] + ext)
    if dest.exists():
        return dest
    r = get(client, url)
    if not r or not (min_kb * 1024 <= len(r.content) <= max_mb * 1024 * 1024):
        return None
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(r.content)
    return dest


def _hex6(h):
    h = h.lstrip("#").lower()
    return "".join(c * 2 for c in h) if len(h) == 3 else h


def style_from_css(css):
    """Most-used saturated colors and font families (greys/black/white are skipped)."""
    colors = Counter()
    for h in re.findall(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b", css):
        h = _hex6(h)
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
        if max(r, g, b) - min(r, g, b) >= 24:
            colors["#" + h] += 1
    fonts = Counter()
    for decl in re.findall(r"font-family\s*:\s*([^;}{]+)", css, re.I):
        f = decl.split(",")[0].strip(" '\"").strip()
        if f and f.lower() not in GENERIC_FONTS and not f.startswith(("var(", "-")):
            fonts[f] += 1
    for fam in re.findall(r"fonts\.googleapis\.com/css2?\?family=([^&:\"';]+)", css):
        fonts[fam.replace("+", " ")] += 2
    return [c for c, _ in colors.most_common(6)], [f for f, _ in fonts.most_common(3)]


def collect_site(client, url, raw):
    out = {"url": url, "pages": [], "menu_pdfs": [], "menu_images": [], "photos": [], "palette": [], "fonts": []}
    home = get(client, url)
    if not home:
        out["error"] = "site did not load"
        return out
    base = str(home.url)
    host = urlparse(base).netloc
    pages = {base: home.text}
    out["social"] = list(dict.fromkeys(
        a["href"] for a in BeautifulSoup(home.text, "html.parser").find_all("a", href=True)
        if re.search(r"instagram\.com/[A-Za-z0-9._]+", a["href"])))[:3]
    for a in BeautifulSoup(home.text, "html.parser").find_all("a", href=True):
        if len(pages) >= config.MAX_SITE_PAGES:
            break
        href = urljoin(base, a["href"]).split("#")[0]
        if urlparse(href).netloc != host or href in pages or href.lower().endswith(".pdf"):
            continue
        if any(h in (href + " " + a.get_text(" ")).lower() for h in PAGE_HINTS):
            r = get(client, href)
            if r and "html" in r.headers.get("content-type", ""):
                pages[href] = r.text

    pdfs, menu_imgs, imgs, css_urls, css_text = [], [], [], [], ""
    (raw / "pages").mkdir(parents=True, exist_ok=True)
    for i, (purl, html) in enumerate(pages.items()):
        s = BeautifulSoup(html, "html.parser")
        css_text += " ".join(t.get_text() for t in s.find_all("style")) + " ".join(t["style"] for t in s.find_all(style=True))
        css_urls += [urljoin(purl, l["href"]) for l in s.find_all("link", href=True) if "stylesheet" in (l.get("rel") or [])]
        css_text += " ".join(l["href"] for l in s.find_all("link", href=True) if "fonts.googleapis" in l["href"])
        for a in s.find_all("a", href=True):
            if a["href"].lower().split("?")[0].endswith(".pdf"):
                pdfs.append(urljoin(purl, a["href"]))
        for img in s.find_all("img"):
            src = img.get("data-src") or img.get("src")
            if not src or src.startswith("data:"):
                continue
            src = urljoin(purl, src)
            path = urlparse(src).path.lower()
            hay = src.lower() + " " + (img.get("alt") or "").lower()
            if not path.endswith(IMG_EXT) or any(w in hay for w in SKIP_IMG):
                continue
            (menu_imgs if re.search(r"menu|menú|carta", hay) else imgs).append(src)
        for t in s(["script", "style", "noscript"]):
            t.decompose()
        text = re.sub(r"\s+", " ", s.get_text(" ")).strip()
        (raw / "pages" / f"{i:02d}.txt").write_text(text, "utf-8")
        out["pages"].append({"url": purl, "text": text[:config.MAX_PAGE_CHARS]})

    for cu in list(dict.fromkeys(css_urls))[:3]:
        r = get(client, cu)
        if r:
            css_text += " " + r.text
    out["palette"], out["fonts"] = style_from_css(css_text)

    def dl(urls, sub, limit, max_mb, min_kb):
        got = []
        for u in dict.fromkeys(urls):
            if len(got) >= limit:
                break
            f = fetch_file(client, u, raw / sub, max_mb, min_kb)
            if f:
                got.append(str(f))
        return got

    out["menu_pdfs"] = dl(pdfs, "menu", config.MAX_MENU_PDFS, 10, 1)
    out["menu_images"] = dl(menu_imgs, "menu", config.MAX_MENU_IMAGES, 8, 10)
    out["photos"] = dl(imgs, "photos", config.MAX_SITE_PHOTOS, 8, 15)
    return out


def photo_files(d, source, limit=None):
    files = sorted(p for p in (d / "photos" / source).glob("*") if p.suffix.lower() in IMG_EXT)
    return [str(p) for p in files[:limit or config.MAX_PHOTOS_PER_SOURCE]]


def process(con, p, audit, refresh, do_research=True, collect_only=False, scrape_sources=()):
    d = store.lead_dir(p)
    prof, raw = d / "profile", d / "raw"
    models = {"fast": config.MODEL_FAST, "strong": config.MODEL_STRONG}

    def cached(name, fn):
        f = prof / f"{name}.json"
        if f.exists() and not refresh:
            return json.loads(f.read_text("utf-8"))
        val = fn()
        if val is not None:
            f.write_text(json.dumps(val, ensure_ascii=False, indent=2), "utf-8")
        return val

    url = None
    if audit and audit["web_type"] == "website" and audit["http_ok"]:
        url = audit["final_url"] or p["website"]
    with httpx.Client() as client:
        site = cached("site", lambda: collect_site(client, url, raw)) if url else None
    site = site or {}
    tags = json.loads(p["tags_json"] or "{}")
    notes_f = d / "notes.txt"
    notes = notes_f.read_text("utf-8", errors="ignore")[:6000] if notes_f.exists() else ""
    page_text = "\n\n".join(f"[{pg['url']}]\n{pg['text']}" for pg in site.get("pages", []))[:20000]
    comps = cached("competitors", lambda: research.competitors(con, p))
    scraped = None
    if scrape_sources:                            # opt-in: keyless Maps / Instagram scrape (scrape.py)
        from leadgen.enrichment import scrape
        scraped = cached("scrape", lambda: scrape.collect(p, tags, site, d, scrape_sources))
    elif (prof / "scrape.json").exists():         # earlier scrape still informs this run
        scraped = json.loads((prof / "scrape.json").read_text("utf-8"))

    if collect_only:                              # no Claude/API calls: gather files, write context.md
        ctx = write_context(d, p, audit, tags, notes, site, comps, scraped)
        print(f"  collected -> {ctx}")
        return

    menu = None
    pdfs, menu_imgs = site.get("menu_pdfs", []), site.get("menu_images", [])
    if pdfs or menu_imgs or (audit and audit["has_menu_text"]):
        print("  extracting menu...")
        menu = cached("menu", lambda: llm.extract_menu(page_text, pdfs, menu_imgs))

    print("  summarizing site/notes...")
    facts = cached("facts", lambda: llm.site_facts(tags, page_text, notes))

    presence = None
    if do_research:
        print("  researching reviews / social / working state (web search)...")
        presence = cached("presence", lambda: research.presence(p, tags, site, notes, audit))
    elif (prof / "presence.json").exists():      # --no-research still reuses earlier research
        presence = json.loads((prof / "presence.json").read_text("utf-8"))

    photo_runs, missing = {}, []
    sources = {"instagram": photo_files(d, "instagram"), "maps": photo_files(d, "maps"),
               "site": site.get("photos", [])[:config.MAX_SITE_PHOTOS]}
    for src, files in sources.items():
        if not files:
            if src != "site":
                missing.append(src)
            continue
        print(f"  analyzing {len(files)} {src} photos...")
        res = cached(f"photos_{src}", lambda src=src, files=files: llm.analyze_photos(src, files))
        if res:
            photo_runs[src] = res

    payload = {
        "restaurant": {"name": p["name"], "area": p["area"], "address": p["address"], "phone": p["phone"],
                       "map_link": p["maps_url"], "osm_tags": tags},
        "current_web_presence": {
            "type": audit["web_type"] if audit else "unknown", "url": url or p["website"],
            "web_score": audit["web_score"] if audit else None, "issues": (audit["issues"] if audit else "") or ""},
        "site_palette": site.get("palette", []), "site_fonts": site.get("fonts", []),
        "site_facts": facts, "menu": menu, "online_presence": presence, "competitors": comps, "photo_analyses": photo_runs, "pasted_notes": notes, "scraped_public_pages": scraped,
        "missing_photo_sources": missing,
    }
    print("  synthesizing profile...")
    profile = cached("profile", lambda: llm.synthesize(payload))
    finish(con, p, profile, missing, models)


def adopt_researched_website(con, p):
    """If research found the brand's own website for a place OSM lists without one, audit it so the lead stops
    showing "no website". Skipped silently when the page does not load or does not match the business."""
    f = store.lead_dir(p, create=False) / "profile" / "presence.json"
    audit = con.execute("SELECT web_type FROM audits WHERE place_id=?", (p["place_id"],)).fetchone()
    if not f.exists() or (audit and audit[0] == "website"):
        return
    try:
        platforms = json.loads(f.read_text("utf-8")).get("platforms", [])
        url = next((x.get("url") for x in platforms if x.get("found") and x.get("url")
                    and x.get("platform", "").lower() in ("brand website", "website", "own website")), None)
        if url:
            from leadgen.audit import audit as audit_mod
            with httpx.Client() as client:
                if audit_mod.adopt_website(con, client, p, url, "website found by research"):
                    print(f"  website found by research: {url}; audit updated")
    except Exception as exc:
        print(f"  could not audit the researched website: {exc}")


def finish(con, p, profile, missing, models):
    """Record the profile and move the lead approved -> enriched."""
    con.execute("INSERT OR REPLACE INTO lead_profile VALUES (?,?,?,?,?)",
                (p["place_id"], json.dumps(profile, ensure_ascii=False), None, json.dumps(models), time.time()))
    if store.get_status(con, p["place_id"]) == "approved":
        store.set_status(con, p["place_id"], "enriched")
    else:
        con.commit()
    adopt_researched_website(con, p)
    status = (profile.get("operating_status") or {}).get("verdict")
    if status in ("likely_closed", "closed"):
        print(f"  WARNING: research suggests this restaurant is {status.replace('_', ' ')}; check before pitching")
    print("  profile saved" + (f"  (no photos in: {', '.join(missing)})" if missing else ""))


def write_context(d, p, audit, tags, notes, site, comps, scraped):
    """leads/<slug>/context.md: everything collected for one lead, for an LLM session (e.g. Claude Code) to analyze."""
    rel = lambda f: Path(f).as_posix()
    photos = {src: photo_files(d, src) for src in store.PHOTO_SOURCES}
    none = "(none: ask the user for screenshots)"
    L = [f"# Collected data: {p['name']}", "",
         f"- place_id: `{p['place_id']}` · area: {p['area']} · address: {p['address'] or 'unknown'} · phone: {p['phone'] or 'unknown'}",
         f"- OSM tags: `{json.dumps(tags, ensure_ascii=False)}`",
         f"- Web audit: type={audit['web_type'] if audit else 'unknown'}, score={audit['web_score'] if audit else '-'}, "
         f"url={(audit['final_url'] if audit else None) or p['website'] or 'none'}",
         f"- Audit issues: {(audit['issues'] if audit else '') or 'none'}", "",
         "## Pasted notes (e.g. Instagram bio/captions)", notes or "(none)", "",
         "## Own site", f"- URL: {site.get('url', '(no working website)')}" + (f" · error: {site['error']}" if site.get("error") else ""),
         f"- Palette (most used saturated colors): {', '.join(site.get('palette', [])) or '-'}",
         f"- Fonts: {', '.join(site.get('fonts', [])) or '-'}",
         f"- Menu PDFs: {', '.join(rel(f) for f in site.get('menu_pdfs', [])) or '-'}",
         f"- Menu images: {', '.join(rel(f) for f in site.get('menu_images', [])) or '-'}",
         f"- Site photos: {', '.join(rel(f) for f in site.get('photos', [])) or '-'}", ""]
    for pg in site.get("pages", []):
        L += [f"### Page text: {pg['url']}", pg["text"], ""]
    L += ["## Dropped-in photos"] + [f"- {src}: {', '.join(rel(f) for f in files) or none}" for src, files in photos.items()]
    listed = {Path(f).name for f in site.get("menu_pdfs", []) + site.get("menu_images", [])}
    dropped = sorted(f for f in (d / "raw" / "menu").glob("*") if f.is_file() and f.name not in listed)
    L += [f"- menu files dropped into raw/menu: {', '.join(rel(f) for f in dropped) or '(none)'}"]
    from leadgen.enrichment import scrape
    L += [""] + scrape.context_section(scraped)
    L += ["## Competitors nearby (from leads.db)", f"{comps.get('insight', 'n/a')}", "```json",
          json.dumps(comps, ensure_ascii=False, indent=1), "```", "",
          "## To finish this lead",
          "1. Analyze the files above (view the images, read menu PDFs); research reviews/Instagram/TripAdvisor/closure signals on the web.",
          f"2. Write `{rel(d / 'profile' / 'profile.json')}` following `schemas.json` (key `profile`); optionally `menu.json` (key `menu`), `presence.json` (key `presence`) and `design_system.json` (key `design_system`).",
          f"3. Run `python ingest.py \"{p['name']}\"` to save the profile and mark the lead enriched."]
    (d / "schemas.json").write_text(json.dumps(
        {"profile": llm.PROFILE_SCHEMA, "menu": llm.MENU_SCHEMA, "presence": llm.PRESENCE_SCHEMA,
         "design_system": llm.DESIGN_SYSTEM_SCHEMA}, ensure_ascii=False, indent=1), "utf-8")
    out = d / "context.md"
    out.write_text("\n".join(L) + "\n", "utf-8")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="name or place_id (also re-processes already enriched leads)")
    ap.add_argument("--refresh", action="store_true", help="ignore cached LLM results")
    ap.add_argument("--no-research", action="store_true", help="skip the web-search research step (cheaper)")
    ap.add_argument("--collect-only", action="store_true",
                    help="no API key needed: crawl site + competitors and write leads/<slug>/context.md for a Claude Code session to analyze; then run ingest.py")
    ap.add_argument("--scrape", nargs="?", const="maps,instagram", metavar="SOURCES",
                    help="also scrape the public Google Maps listing and Instagram profile without any API key "
                         "(maps,instagram; see scrape.py for caveats). Results are cached; --refresh redoes them")
    args = ap.parse_args()
    sources = tuple(x for x in (args.scrape or "").split(",") if x)
    if bad := [x for x in sources if x not in ("maps", "instagram")]:
        ap.error(f"unknown scrape source: {', '.join(bad)}")
    con = store.connect()
    try:
        audits = {r["place_id"]: r for r in con.execute("SELECT * FROM audits")}
    except Exception:
        audits = {}
    if args.only:
        leads = store.find(con, args.only)
    else:
        leads = con.execute("SELECT p.* FROM places p JOIN lead_status s USING(place_id) WHERE s.status='approved'").fetchall()
    if not leads:
        print("No leads to process. Approve some first: python approve.py approved <name-or-place_id>")
        return
    failed = 0
    for p in leads:
        print(f"[{p['name']}]")
        try:
            process(con, p, audits.get(p["place_id"]), args.refresh, not args.no_research, args.collect_only, sources)
        except Exception as e:
            failed += 1
            print(f"  FAILED: {type(e).__name__}: {e}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
