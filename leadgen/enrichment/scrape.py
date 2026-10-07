"""Optional, keyless collection of a lead's public Google Maps listing and Instagram profile.

Usage: python scrape.py NAME_OR_ID [--only maps|instagram] [--headed]
       (normally run through `python enrich.py --scrape`, or the "Collect Maps and Instagram" option in the app)

Drives a headless Chromium (Playwright) like a logged-out visitor: no login, no API key, no cookies kept.
Everything is best effort. Both sites change their markup often and can stop serving a visitor at any time;
when that happens the source is recorded as `blocked` / `not_found` and the run carries on. Nothing here tries
to get past a login wall, a captcha or a rate limit: it stops and says so.

Results: leads/<slug>/profile/scrape.json, plus photos saved as photos/{maps,instagram}/scrape-NN.jpg (the
files the enrichment already reads). Anything scraped is untrusted text about the restaurant.

Setup:  pip install playwright && python -m playwright install chromium
Terms:  scraping Google Maps and Instagram is against their terms of use. It is opt-in, one lead per run,
        slow, and only reads public pages; use it knowingly.
"""
import argparse
import io
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlparse

from leadgen import config
from leadgen import store

SOURCES = ("maps", "instagram")
MAX_REVIEWS = 8
MAX_POSTS = 12
PHOTO_PREFIX = "scrape-"
IG_APP_ID = "936619743392459"          # public web-app id the instagram.com site itself sends
BLOCK_MARKERS = ("unusual traffic", "/sorry/", "captcha", "tráfico inusual")


class Blocked(Exception):
    pass


def installed():
    """Cheap check (no browser launch): the Playwright package is importable."""
    import importlib.util
    return importlib.util.find_spec("playwright") is not None


def available():
    """Playwright and a Chromium build are installed."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            return Path(p.chromium.executable_path).exists()
    except Exception:
        return False


def instagram_handle(place, tags, site):
    """The restaurant's own Instagram handle from OSM tags, its stored link, or links found on its site."""
    cands = [tags.get(k) for k in ("contact:instagram", "instagram")] + [place["website"]] + list((site or {}).get("social", []))
    for c in cands:
        if not c:
            continue
        m = re.search(r"instagram\.com/([A-Za-z0-9._]{1,30})", c) or re.fullmatch(r"@?([A-Za-z0-9._]{1,30})", c.strip())
        if m and m.group(1).lower() not in ("p", "reel", "explore", "accounts", "stories", "tv"):
            return m.group(1).rstrip("/")
    return None


def _num(s):
    """'1,234' / '1.234' / '12.5K' / '1,2 mil' -> int."""
    s = (s or "").lower().replace("\xa0", " ").strip()
    m = re.match(r"([\d.,]+)\s*(mil|k|m)?", s)
    if not m:
        return None
    n, unit = m.group(1), m.group(2)
    if unit:
        n = float(n.replace(",", ".")) if n.count(",") + n.count(".") == 1 else float(re.sub(r"[.,]", "", n))
        return int(n * {"k": 1e3, "mil": 1e3, "m": 1e6}[unit])
    return int(re.sub(r"[.,]", "", n)) if re.sub(r"[.,]", "", n).isdigit() else None


def _save_photo(blob, dest):
    """Verify with Pillow, shrink to config.MAX_IMAGE_PX, write as JPEG. Returns False for junk."""
    from PIL import Image
    try:
        im = Image.open(io.BytesIO(blob))
        im.load()
        if min(im.size) < 200:
            return False
        im = im.convert("RGB")
        im.thumbnail((config.MAX_IMAGE_PX, config.MAX_IMAGE_PX))
        im.save(dest, "JPEG", quality=85)
        return True
    except Exception:
        return False


def _download(ctx, urls, folder, limit):
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob(PHOTO_PREFIX + "*"):          # re-scraping replaces earlier scrapes, never the user's own files
        old.unlink()
    saved = []
    for u in dict.fromkeys(urls):
        if len(saved) >= limit:
            break
        try:
            r = ctx.request.get(u, timeout=20000)
            if r.ok and _save_photo(r.body(), folder / f"{PHOTO_PREFIX}{len(saved) + 1:02d}.jpg"):
                saved.append(f"{PHOTO_PREFIX}{len(saved) + 1:02d}.jpg")
        except Exception:
            continue
        time.sleep(0.4)
    return saved


def _check_block(page):
    t = (page.url + " " + page.title()).lower()
    if any(m in t for m in BLOCK_MARKERS):
        raise Blocked("the site asked for a captcha / reported unusual traffic")


# --- Google Maps -----------------------------------------------------------------

def _text(page, sel):
    try:
        el = page.query_selector(sel)
        return el.inner_text().strip() if el else None
    except Exception:
        return None


def _attr(page, sel, attr):
    try:
        el = page.query_selector(sel)
        return el.get_attribute(attr) if el else None
    except Exception:
        return None


def _same(ours, theirs):
    a, b = store._norm(ours), store._norm(theirs or "")
    return bool(a and b and (a in b or b in a))


def scrape_maps(page, ctx, place, d):
    at = f"/@{place['lat']},{place['lng']},18z" if place["lat"] and place["lng"] else ""
    res = None
    for q in (" ".join(x for x in [place["name"], place["address"], "Medellín"] if x), f"{place['name']} {place['area']} Medellín"):
        page.goto(f"https://www.google.com/maps/search/{quote(q)}{at}?hl=es", wait_until="domcontentloaded", timeout=45000)
        _check_block(page)
        for label in ("Rechazar todo", "Reject all"):             # cookie wall (EU); decline
            b = page.query_selector(f'button:has-text("{label}")')
            if b:
                b.click()
                page.wait_for_load_state("domcontentloaded")
                break
        try:
            page.wait_for_selector('h1.DUwDvf, a.hfpxzc, div[role="feed"]', timeout=15000)
        except Exception:
            pass
        if "/maps/place/" in page.url.split("?")[0] and (_text(page, "h1") or "") not in ("Resultados", "Results"):
            break
        hits = page.query_selector_all('a.hfpxzc[href*="/maps/place/"]')       # result list: open the hit that is our restaurant
        pick = next((h for h in hits if _same(place["name"], h.get_attribute("aria-label"))), None)
        if pick:
            pick.click()
            page.wait_for_url(re.compile(r"/maps/place/.*!3d"), timeout=20000)
            break
        res = {"status": "no_match" if hits else "not_found",
               "note": "Maps did not list this restaurant by name." if hits else "No results.",
               "candidates": [h.get_attribute("aria-label") for h in hits[:5]]}
    else:
        return res
    page.wait_for_selector("h1.DUwDvf", timeout=20000)
    time.sleep(2.5)
    name = _text(page, "h1.DUwDvf") or _text(page, "h1")
    out = {"status": "ok", "url": page.url.split("?")[0], "name": name,
           "name_match": _same(place["name"], name)}
    if not out["name_match"]:                                  # never keep another restaurant's data or photos
        return {"status": "no_match", "note": f"Maps opened '{name}', not this restaurant.", "candidates": [name]}
    rating_label = _attr(page, 'div.F7nice span[aria-hidden="true"]', "aria-label") or _attr(page, '[role="img"][aria-label*="estrellas"], [role="img"][aria-label*="stars"]', "aria-label")
    m = re.search(r"(\d[.,]\d)", rating_label or _text(page, "div.F7nice") or "")
    out["rating"] = float(m.group(1).replace(",", ".")) if m else None
    cnt = _attr(page, 'span[aria-label*="reseñas"], span[aria-label*="reviews"]', "aria-label") or _text(page, "div.F7nice")
    m = re.search(r"\(?([\d.,]+)\)?\s*(?:reseñas|reviews)?", (cnt or "").split("\n")[-1])
    out["review_count"] = _num(m.group(1)) if m else None
    out["category"] = _text(page, 'button[jsaction*="category"]')
    out["address"] = (_attr(page, 'button[data-item-id="address"]', "aria-label") or "").split(":", 1)[-1].strip() or None
    out["phone"] = (_attr(page, 'button[data-item-id^="phone"]', "aria-label") or "").split(":", 1)[-1].strip() or None
    out["website"] = _attr(page, 'a[data-item-id="authority"]', "href")
    body = (_text(page, "div[role=main]") or "").lower()
    out["closed_flag"] = ("permanently closed" if re.search(r"permanently closed|cerrado permanentemente", body)
                          else "temporarily closed" if re.search(r"temporarily closed|cerrado temporalmente", body) else None)
    out["hours"] = [r.inner_text().replace("\n", " ").strip() for r in page.query_selector_all("table.eK4R0e tr, table.WgFkxc tr")][:7]
    out["attributes"] = [a for a in (e.get_attribute("aria-label") for e in page.query_selector_all('div[role="group"] [aria-label]')) if a][:20]

    imgs = [i.get_attribute("src") for i in page.query_selector_all('button[jsaction*="heroHeaderImage"] img, img[src*="googleusercontent.com/p/"], img[src*="gps-cs"]')]
    # Reviews: open the reviews tab, sorted as Google serves them (relevance); a handful is enough for a sales read.
    tab = page.query_selector('button[role="tab"][aria-label*="eseñas"], button[role="tab"][aria-label*="eviews"]')
    reviews = []
    if tab:
        tab.click()
        time.sleep(2)
        seen = set()
        for r in page.query_selector_all("div[data-review-id]"):
            rid = r.get_attribute("data-review-id")
            if rid in seen or len(reviews) >= MAX_REVIEWS:
                continue
            seen.add(rid)
            stars = _attr_el(r, 'span[role="img"]', "aria-label")
            reviews.append({"stars": int(re.match(r"\d", stars or "0").group(0)) if re.match(r"\d", stars or "") else None,
                            "when": _text_el(r, "span.rsqaWe"), "text": _text_el(r, "span.wiI7pd")})
        imgs += [i.get_attribute("src") for i in page.query_selector_all('div[data-review-id] button[style*="googleusercontent"], div[data-review-id] img[src*="googleusercontent.com/p/"]')]
    out["reviews"] = [r for r in reviews if r["text"] or r["stars"]]
    big = [re.sub(r"=[wsh]\d+[^/]*$", "=w1200", u) for u in imgs if u and "googleusercontent" in u and "/a/" not in u and "/a-/" not in u]
    out["photos"] = _download(ctx, big, d / "photos" / "maps", config.MAX_PHOTOS_PER_SOURCE)
    return out


def _text_el(el, sel):
    x = el.query_selector(sel)
    return x.inner_text().strip() if x else None


def _attr_el(el, sel, attr):
    x = el.query_selector(sel)
    return x.get_attribute(attr) if x else None


# --- Instagram -------------------------------------------------------------------

def scrape_instagram(page, ctx, handle, d):
    out = {"status": "ok", "handle": handle, "url": f"https://www.instagram.com/{handle}/"}
    # 1) the web-app JSON the public profile page itself loads; it answers logged-out visitors only sometimes
    api = ctx.request.get(f"https://i.instagram.com/api/v1/users/web_profile_info/?username={handle}",
                          headers={"x-ig-app-id": IG_APP_ID, "referer": out["url"]}, timeout=20000)
    user = None
    if api.ok:
        try:
            user = (api.json().get("data") or {}).get("user")
        except Exception:
            user = None
    elif api.status == 404:
        return {"status": "not_found", "handle": handle}
    if user:
        media = [e["node"] for e in (user.get("edge_owner_to_timeline_media") or {}).get("edges", [])][:MAX_POSTS]
        posts = []
        for n in media:
            caps = (n.get("edge_media_to_caption") or {}).get("edges") or []
            posts.append({"date": datetime.fromtimestamp(n["taken_at_timestamp"], timezone.utc).date().isoformat() if n.get("taken_at_timestamp") else None,
                          "caption": (caps[0]["node"]["text"][:400] if caps else ""), "likes": (n.get("edge_liked_by") or {}).get("count"),
                          "comments": (n.get("edge_media_to_comment") or {}).get("count"), "video": bool(n.get("is_video")),
                          "image": n.get("display_url")})
        out.update(full_name=user.get("full_name"), bio=user.get("biography"), external_url=user.get("external_url"),
                   followers=(user.get("edge_followed_by") or {}).get("count"), following=(user.get("edge_follow") or {}).get("count"),
                   post_count=(user.get("edge_owner_to_timeline_media") or {}).get("count"), is_private=user.get("is_private"),
                   business_category=user.get("category_name"), posts=[{k: v for k, v in p.items() if k != "image"} for p in posts])
        dates = sorted(p["date"] for p in posts if p["date"])
        out["last_post"] = dates[-1] if dates else None
        out["photos"] = _download(ctx, [p["image"] for p in posts if p["image"]], d / "photos" / "instagram", config.MAX_PHOTOS_PER_SOURCE)
        return out
    # 2) fall back to the page's social-preview meta tags: counts and bio only, no posts
    page.goto(out["url"], wait_until="domcontentloaded", timeout=45000)
    time.sleep(2)
    _check_block(page)
    if "/accounts/login" in page.url:
        return {"status": "blocked", "handle": handle, "note": "Instagram asked for a login; nothing was read."}
    desc = _attr(page, 'meta[property="og:description"]', "content") or ""
    title = _attr(page, 'meta[property="og:title"]', "content") or ""
    m = re.search(r"([\d.,]+[KMkm]?|[\d.,]+ mil)\s+(?:Followers|seguidores)[^\d]+([\d.,]+[KMkm]?)\s+(?:Following|seguidos)[^\d]+([\d.,]+[KMkm]?)\s+(?:Posts|publicaciones)", desc, re.I)
    if not m and not title:
        return {"status": "blocked", "handle": handle, "note": "Instagram served no public profile data to a logged-out visitor."}
    out.update(full_name=re.sub(r"\s*\(@.*", "", title) or None,
               followers=_num(m.group(1)) if m else None, following=_num(m.group(2)) if m else None,
               post_count=_num(m.group(3)) if m else None, bio=desc.split(" - ", 1)[-1][:400] if " - " in desc else None,
               posts=[], note="Only the public preview was available (no posts).")
    og = _attr(page, 'meta[property="og:image"]', "content")
    out["photos"] = _download(ctx, [og] if og else [], d / "photos" / "instagram", 1)
    return out


# --- entry points ----------------------------------------------------------------

def collect(place, tags, site, d, sources=SOURCES, headed=False, log=print):
    """Scrape the requested sources for one lead. Returns {source: result}; never raises for a blocked source."""
    from playwright.sync_api import sync_playwright
    res = {"scraped_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    handle = instagram_handle(place, tags, site)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not headed)
        ctx = browser.new_context(user_agent=config.BROWSER_UA, locale="es-CO", viewport={"width": 1280, "height": 900},
                                  timezone_id="America/Bogota")
        page = ctx.new_page()
        try:
            for src in sources:
                for old in (d / "photos" / src).glob(PHOTO_PREFIX + "*"):   # a fresh scrape never keeps the last one's photos
                    old.unlink()
                log(f"  scraping {src}...")
                try:
                    if src == "maps":
                        res["maps"] = scrape_maps(page, ctx, place, d)
                    elif not handle:
                        res["instagram"] = {"status": "no_handle", "note": "No Instagram link in the OSM tags or on the site."}
                    else:
                        res["instagram"] = scrape_instagram(page, ctx, handle, d)
                except Blocked as e:
                    res[src] = {"status": "blocked", "note": str(e)}
                except Exception as e:                      # timeouts, changed markup: record and move on
                    res[src] = {"status": "error", "note": f"{type(e).__name__}: {str(e)[:200]}"}
                r = res[src]
                log(f"    {src}: {r['status']}" + (f" ({len(r.get('photos', []))} photos)" if r["status"] == "ok" else f" - {r.get('note', '')}"))
                time.sleep(2)
        finally:
            browser.close()
    if res.get("maps"):                                  # feeds the premium quality score (quality.py)
        from leadgen.scoring import quality
        con = store.connect()
        try:
            quality.record(con, place["place_id"], res["maps"])
        finally:
            con.close()
    (d / "profile").mkdir(parents=True, exist_ok=True)
    (d / "profile" / "scrape.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), "utf-8")
    return res


def context_section(res):
    """Markdown for context.md. `res` may be None (scraping not requested)."""
    if not res:
        return ["## Scraped public pages", "(not collected; run with --scrape)", ""]
    L = ["## Scraped public pages (untrusted; logged-out visitor, best effort)", f"- scraped at {res.get('scraped_at')}"]
    m = res.get("maps")
    if m:
        if m["status"] != "ok":
            L.append(f"- Google Maps: {m['status']} {m.get('note', '')}")
        else:
            L += [f"- Google Maps: {m.get('name')} · rating {m.get('rating')} from {m.get('review_count')} reviews · {m.get('category')} · "
                  f"matches our name: {m.get('name_match')} · {m.get('closed_flag') or 'not flagged closed'}",
                  f"  - address: {m.get('address')} · phone: {m.get('phone')} · website: {m.get('website')} · {m.get('url')}",
                  f"  - hours: {'; '.join(m.get('hours') or []) or '-'}", f"  - photos saved in photos/maps/: {len(m.get('photos', []))}"]
            L += [f"  - review ({r['stars']}★, {r['when']}): {(r['text'] or '')[:300]}" for r in m.get("reviews", [])]
    i = res.get("instagram")
    if i:
        if i["status"] != "ok":
            L.append(f"- Instagram: {i['status']} {i.get('note', '')}")
        else:
            L += [f"- Instagram @{i['handle']}: {i.get('followers')} followers · {i.get('post_count')} posts · last post {i.get('last_post') or 'unknown'} · "
                  f"link in bio: {i.get('external_url') or '-'} · {i.get('business_category') or ''}",
                  f"  - bio: {(i.get('bio') or '-')!r}", f"  - photos saved in photos/instagram/: {len(i.get('photos', []))}"]
            L += [f"  - post {p['date']} ({p['likes']} likes): {p['caption'][:200]!r}" for p in i.get("posts", [])]
    return L + [""]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name", help="name or place_id")
    ap.add_argument("--only", choices=SOURCES)
    ap.add_argument("--headed", action="store_true", help="show the browser (to see why a source fails)")
    args = ap.parse_args()
    con = store.connect()
    leads = store.find(con, args.name)
    if not leads:
        raise SystemExit("No such lead.")
    for p in leads:
        d = store.lead_dir(p)
        print(f"[{p['name']}]")
        site = json.loads((d / "profile" / "site.json").read_text("utf-8")) if (d / "profile" / "site.json").exists() else {}
        collect(p, json.loads(p["tags_json"] or "{}"), site, d, (args.only,) if args.only else SOURCES, args.headed)


if __name__ == "__main__":
    main()
