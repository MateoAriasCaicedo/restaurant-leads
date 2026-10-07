"""Audit each restaurant's web presence.

Usage: python audit.py [--refresh] [--only PLACE_ID] [--discover] [--perf] [--rescore]
Reads places from SQLite, writes table `audits` (one row per place_id).
--refresh re-audits everything; --only re-audits a single place (e.g. osm:node/123).
--discover looks for a website for places OSM lists without one (sitefind.py), auditing any it verifies.
--perf fills in the PageSpeed score of live sites that still lack one (needs no re-crawl).
--rescore recomputes web_score and confidence from the stored audits, offline.
"""
import re
import sqlite3
import sys
import time
from urllib.parse import urlparse

import httpx

from leadgen import config
from leadgen.audit import sitefind
from leadgen.audit import sitesignals
from leadgen.audit import urlcheck

CHEAP_BUILDERS = ("wixsite.com", "blogspot.", "weebly.com", "business.site", "site123", "webnode", "jimdosite", "sites.google.com")


def normalize_url(url):
    """OSM website tags often lack a scheme ("www.foo.co"); add one so urlparse/httpx work."""
    url = (url or "").strip()
    if url and not re.match(r"^https?://", url, re.I):
        url = "http://" + url.lstrip("/")
    return url


def classify(url):
    if not url:
        return "none"
    host = urlparse(url).netloc.lower().replace("www.", "")
    if any(host == d or host.endswith("." + d) for d in config.SOCIAL_DOMAINS):
        return "social_only"
    return "website"


COLUMNS = [
    "place_id", "web_type", "final_url", "http_ok", "https", "viewport", "has_title", "has_meta_desc", "has_h1",
    "has_menu_text", "menu_pdf_only", "has_whatsapp", "has_tel", "has_reserve", "has_order", "has_schema",
    "cheap_builder", "copyright_year", "page_kb", "mobile_perf", "web_score", "issues", "audited_at",
    "confidence", "evidence", "js_shell", "url_source",
]
# Columns added after the first release; init() adds them to an existing audits table.
ADDED = {"confidence": "TEXT", "evidence": "TEXT", "js_shell": "INTEGER", "url_source": "TEXT"}


def init(con):
    urlcheck.init(con)
    con.execute(
        """CREATE TABLE IF NOT EXISTS audits (
            place_id TEXT PRIMARY KEY, web_type TEXT, final_url TEXT, http_ok INTEGER,
            https INTEGER, viewport INTEGER, has_title INTEGER, has_meta_desc INTEGER,
            has_h1 INTEGER, has_menu_text INTEGER, menu_pdf_only INTEGER, has_whatsapp INTEGER,
            has_tel INTEGER, has_reserve INTEGER, has_order INTEGER, has_schema INTEGER,
            cheap_builder INTEGER, copyright_year INTEGER, page_kb REAL, mobile_perf REAL,
            web_score INTEGER, issues TEXT, audited_at REAL,
            confidence TEXT, evidence TEXT, js_shell INTEGER, url_source TEXT)"""
    )
    have = {r[1] for r in con.execute("PRAGMA table_info(audits)")}
    for col, typ in ADDED.items():
        if col not in have:
            con.execute(f"ALTER TABLE audits ADD COLUMN {col} {typ}")
    con.execute(
        """CREATE TABLE IF NOT EXISTS url_discovery (
            place_id TEXT PRIMARY KEY, tried_at REAL, found_url TEXT, note TEXT)""")


_PS = {"fails": 0, "off": False}   # circuit breaker: the free API 429s hard without a key


def pagespeed(client, url):
    """Free PageSpeed Insights mobile performance (0-100). Returns None on failure.
    After 2 sites in a row exhaust their retries, it is skipped for the rest of the run."""
    if _PS["off"]:
        return None
    params = {"url": url, "strategy": "mobile", "category": "performance"}
    if config.GOOGLE_API_KEY:
        params["key"] = config.GOOGLE_API_KEY
    for attempt in range(3):
        try:
            r = client.get("https://www.googleapis.com/pagespeedonline/v5/runPagespeed", params=params, timeout=60)
            if r.status_code == 200:
                _PS["fails"] = 0
                return r.json()["lighthouseResult"]["categories"]["performance"]["score"] * 100
            if r.status_code in (429, 500, 502, 503):
                print(f"  PageSpeed {r.status_code}, retrying in {5 * (attempt + 1)}s")
                time.sleep(5 * (attempt + 1))
                continue
            print(f"  PageSpeed {r.status_code} for {url}; leaving it unmeasured")
            return None
        except Exception as e:
            print(f"  PageSpeed error ({type(e).__name__}) for {url}")
            time.sleep(3)
    _PS["fails"] += 1
    if _PS["fails"] >= 2:
        _PS["off"] = True
        print("  PageSpeed keeps failing: skipping it for the rest of this run (left unmeasured; run `python audit.py --perf` later). "
              "Set GOOGLE_API_KEY in .env to raise the free rate limit.")
    return None



def audit_site(client, url, resp=None):
    """Audit one page. `resp` is a response urlcheck already fetched, so the page is not requested twice."""
    out = {"http_ok": 0, "final_url": url, "issues": []}
    r = resp
    if r is None:
        try:
            r = client.get(url, timeout=20, follow_redirects=True, headers={"User-Agent": config.BROWSER_UA})
        except Exception:
            out["issues"].append("site does not load")
            return out
    out["final_url"] = str(r.url)
    out["http_ok"] = 1 if r.status_code < 400 else 0
    if not out["http_ok"]:
        out["issues"].append(f"site returns HTTP {r.status_code}")
        return out
    out["https"] = 1 if str(r.url).startswith("https") else 0
    out.update(sitesignals.parse(r.text))            # None = could not be judged (JavaScript-rendered page)
    host = urlparse(str(r.url)).netloc.lower()
    out["cheap_builder"] = 1 if any(b in host for b in CHEAP_BUILDERS) else 0
    out["page_kb"] = round(len(r.content) / 1024, 1)

    absent = lambda k: out.get(k) == 0
    if absent("https"): out["issues"].append("no HTTPS")
    if absent("viewport"): out["issues"].append("not mobile-friendly (no viewport)")
    if absent("has_title") or absent("has_meta_desc"): out["issues"].append("missing SEO title/description")
    if absent("has_h1"): out["issues"].append("no H1 heading")
    if out.get("menu_pdf_only"): out["issues"].append("menu only as PDF")
    elif absent("has_menu_text"): out["issues"].append("no menu on site")
    if absent("has_whatsapp"): out["issues"].append("no WhatsApp button")
    if absent("has_reserve") and absent("has_order"): out["issues"].append("no reservation or ordering option")
    if absent("has_schema"): out["issues"].append("no structured data for Google")
    if out["cheap_builder"]: out["issues"].append("free/template site builder domain")
    if out["copyright_year"] and out["copyright_year"] < 2023: out["issues"].append(f"outdated (© {out['copyright_year']})")
    return out


# (field, points). With the extras in web_score() these sum to 100 when every signal is known.
SIGNALS = (("https", 10), ("viewport", 15), ("has_title", 8), ("has_meta_desc", 7), ("has_h1", 3),
           ("has_menu_text", 15), ("has_whatsapp", 8), ("has_tel", 3), ("has_schema", 4))


def web_score(a):
    """0-100, higher = better website. Signals that are unknown (not measured, or not judgeable on a
    JavaScript-rendered page) are left out of both the points earned and the points available, so a missing
    PageSpeed run no longer hands every site the same neutral 8 points."""
    if not a.get("http_ok"):
        return 0
    earned = avail = 0
    for field, pts in SIGNALS:
        v = a.get(field)
        if v is not None:
            avail += pts
            earned += pts * v
    ro = (a.get("has_reserve"), a.get("has_order"))
    if any(v is not None for v in ro):
        avail += 7
        earned += 7 * (1 if any(ro) else 0)
    y = a.get("copyright_year")
    if y:
        avail += 5
        earned += 5 * (y >= 2024)
    perf = a.get("mobile_perf")
    if perf is not None:
        avail += 15
        earned += 15 * perf / 100
    if not avail:
        return 50
    pts = round(100 * earned / avail) - 8 * (a.get("cheap_builder") or 0)
    return max(0, min(100, pts))


def confidence_for(kind, status, name_match, discovery_tried=False):
    """How far to trust this audit as a statement about the real business -> (high|medium|low, why)."""
    if kind == "none":
        if discovery_tried:
            return "medium", "no website in OpenStreetMap; guessed domains checked, none matched"
        return "low", "no website in OpenStreetMap; not verified elsewhere (may be a data gap)"
    if kind == "social_only":
        return "medium", "social page taken from OpenStreetMap; not opened (those sites block bots)"
    if status == "ok":
        if name_match == 1:
            return "high", "page loads and matches the business"
        if name_match == 0:
            return "low", "page loads but does not mention the business (may be the wrong site)"
        return "medium", "page loads; the business could not be fully confirmed on it"
    if status in ("dead", "parked"):
        return "high", "link verified as unusable on every URL variant"
    if status == "blocked":
        return "low", "site blocks automated checks; quality unknown"
    return "low", "site did not answer; may be a temporary outage"


def audit_from_check(client, res, url):
    """Turn a urlcheck result into the audit dict + web score."""
    st = res["status"]
    if st == "ok":
        a = audit_site(client, res["final_url"], res.get("response"))
        if res.get("name_match") == 0:
            a["issues"].append(res["note"])
        if a.get("http_ok"):
            a["mobile_perf"] = pagespeed(client, a["final_url"])
            if a["mobile_perf"] is not None and a["mobile_perf"] < 40:
                a["issues"].append(f"slow on mobile (PageSpeed {a['mobile_perf']:.0f})")
        return a, web_score(a)
    a = {"http_ok": 0, "final_url": url, "issues": []}
    if st == "blocked":
        a["http_ok"] = None
        a["issues"].append(f"site blocks automated checks ({res['note']})")
        return a, 50  # unknown quality: neutral score
    label = {"dead": "website link is dead", "unreachable": "website is down/unreachable", "parked": "website link points to a parked page"}[st]
    a["issues"].append(f"{label}: {res['note']}")
    return a, 0


def due_rows(con, refresh=False, only=None):
    """(place_id, url, name, phone, source) of the places to audit now. `only` forces that one place_id.
    A site found by --discover lives in url_checks, not in places.website, so it is rechecked from there."""
    cutoff = time.time() - config.URL_RECHECK_DAYS * 86400

    def target(r):
        found = r[7] == "discovered" and r[8]
        return (r[8] if found else r[1]), ("discovered" if found else "osm")

    def due(r):
        if refresh or not r[4]:
            return True                      # never audited
        if classify(normalize_url(target(r)[0])) != "website":
            return False
        if r[5] is None:
            return True                      # audited before URL checks existed
        return r[5] != "ok" and r[6] < cutoff  # broken/blocked: recheck once the last check is old enough

    sql = """SELECT p.place_id, p.website, p.name, p.phone, a.place_id, u.status, u.checked_at, a.url_source, u.url
             FROM places p LEFT JOIN audits a USING(place_id) LEFT JOIN url_checks u USING(place_id)"""
    out = lambda r: (r[0], target(r)[0], r[2], r[3], target(r)[1])
    if only:
        return [out(r) for r in con.execute(sql + " WHERE p.place_id=?", (only,))]
    return [out(r) for r in con.execute(sql) if due(r)]


def save_audit(con, pid, kind, a, score, confidence=None, evidence=None, source="osm"):
    row = dict(a, place_id=pid, web_type=kind, web_score=score, issues="; ".join(a["issues"]),
               audited_at=time.time(), confidence=confidence, evidence=evidence, url_source=source)
    con.execute(f"INSERT OR REPLACE INTO audits ({','.join(COLUMNS)}) VALUES ({','.join('?' * len(COLUMNS))})",
                [row.get(c) for c in COLUMNS])
    con.commit()


def audit_one(con, client, pid, url, name, phone="", source="osm", res=None, note=""):
    """Audit one place and store it. `res` is a urlcheck result already in hand (from --discover).
    Returns (web_type, url_check_status or None)."""
    kind = classify(url)
    if kind == "none" and source != "discovered":
        # A site may have been adopted (enrich research, --discover) after this run chose its work list.
        # Audit that site again instead of overwriting it with "no website".
        known = con.execute("""SELECT u.url FROM audits a JOIN url_checks u USING(place_id)
                               WHERE a.place_id=? AND a.url_source='discovered'""", (pid,)).fetchone()
        if known and known[0]:
            url, source, kind, res = known[0], "discovered", classify(known[0]), None
    a, status, match = {"issues": []}, None, None
    if kind == "none":
        a["issues"] = ["no website"]
        score = 0
    elif kind == "social_only":
        a["issues"] = ["only a social/delivery page, no real website"]
        score = 0
    else:
        res = res or urlcheck.check(client, url, name, phone)
        urlcheck.save(con, pid, url, res)
        status, match = res["status"], res.get("name_match")
        print(f"    url: {res['status']} {res['note']}".rstrip())
        a, score = audit_from_check(client, res, url)
    conf, why = confidence_for(kind, status, match)
    if a.get("js_shell"):
        why += "; page is built by JavaScript, so some content checks were inconclusive"
    save_audit(con, pid, kind, a, score, conf, "; ".join(x for x in (note, why) if x), source)
    return kind, status


def run_discovery(con, client):
    """Try to find a website for places OSM lists without one. A verified site is audited like any other."""
    from leadgen.scoring import score as scoring
    con.row_factory = sqlite3.Row
    cutoff = time.time() - config.DISCOVER_RETRY_DAYS * 86400
    places = [p for p in con.execute(
        """SELECT p.* FROM places p JOIN audits a USING(place_id) LEFT JOIN url_discovery d USING(place_id)
           WHERE a.web_type='none' AND (d.place_id IS NULL OR d.tried_at < ?)""", (cutoff,))
        if not scoring.excluded(p)]
    con.row_factory = None
    found = 0
    print(f"Looking for websites of {len(places)} places listed without one")
    for i, p in enumerate(places, 1):
        res, note = sitefind.find(client, p["name"], p["phone"])
        print(f"[{i}/{len(places)}] {p['name']}: {note}")
        con.execute("INSERT OR REPLACE INTO url_discovery VALUES (?,?,?,?)",
                    (p["place_id"], time.time(), res["final_url"] if res else None, note))
        if res:
            found += 1
            audit_one(con, client, p["place_id"], res["final_url"], p["name"], p["phone"], "discovered", res, note)
        else:
            _, why = confidence_for("none", None, None, discovery_tried=True)
            con.execute("UPDATE audits SET confidence='medium', evidence=? WHERE place_id=? AND web_type='none'",
                        (why, p["place_id"]))
        con.commit()
    print(f"Discovery done: {found} website(s) found")


def adopt_website(con, client, place, url, note):
    """Audit a website that research found for a place OSM lists without one (only if the page loads and matches)."""
    from leadgen.audit import urlcheck
    pid = place["place_id"]
    row = con.execute("SELECT web_type FROM audits WHERE place_id=?", (pid,)).fetchone()
    if row and row[0] == "website":
        return False
    url = normalize_url(url)
    if classify(url) != "website":
        return False
    res = urlcheck.check(client, url, place["name"], place["phone"] or "")
    if res["status"] != "ok" or res.get("name_match") == 0:
        return False
    con.execute("INSERT OR REPLACE INTO url_discovery VALUES (?,?,?,?)", (pid, time.time(), res["final_url"], note))
    audit_one(con, client, pid, res["final_url"], place["name"], place["phone"] or "", "discovered", res, note)
    return True


def fill_pagespeed(con, client):
    """Measure PageSpeed for live sites that have none, then rescore them from the stored signals."""
    _PS.update(fails=0, off=False)
    con.row_factory = sqlite3.Row
    rows = con.execute("SELECT * FROM audits WHERE web_type='website' AND http_ok=1 AND mobile_perf IS NULL").fetchall()
    con.row_factory = None
    print(f"Measuring PageSpeed for {len(rows)} sites")
    done = 0
    for r in rows:
        a = dict(r)
        perf = pagespeed(client, a["final_url"])
        if perf is None:
            if _PS["off"]:
                print("PageSpeed is rate limiting; stopping. Try again later or set GOOGLE_API_KEY in .env")
                break
            continue
        a["mobile_perf"] = perf
        issues = [i for i in (a["issues"] or "").split("; ") if i and not i.startswith("slow on mobile")]
        if perf < 40:
            issues.append(f"slow on mobile (PageSpeed {perf:.0f})")
        con.execute("UPDATE audits SET mobile_perf=?, web_score=?, issues=? WHERE place_id=?",
                    (perf, web_score(a), "; ".join(issues), a["place_id"]))
        con.commit()
        done += 1
    print(f"PageSpeed filled for {done}/{len(rows)}")


def rescore(con):
    """Recompute web_score and confidence from what is already stored. No network."""
    con.row_factory = sqlite3.Row
    rows = con.execute(
        """SELECT a.*, u.status AS u_status, u.name_match AS u_match, d.place_id AS tried
           FROM audits a LEFT JOIN url_checks u USING(place_id) LEFT JOIN url_discovery d USING(place_id)""").fetchall()
    con.row_factory = None
    for r in rows:
        a = dict(r)
        score = web_score(a) if a["web_type"] == "website" and a["http_ok"] else a["web_score"]
        conf, why = confidence_for(a["web_type"], a["u_status"], a["u_match"], bool(a["tried"]))
        if a["js_shell"]:
            why += "; page is built by JavaScript, so some content checks were inconclusive"
        if a["url_source"] == "discovered" and a["evidence"]:
            why = a["evidence"].split("; ")[0] + "; " + why
        con.execute("UPDATE audits SET web_score=?, confidence=?, evidence=?, url_source=COALESCE(url_source,'osm') WHERE place_id=?",
                    (score, conf, why, a["place_id"]))
    con.commit()
    print(f"Rescored {len(rows)} audits")


def main(refresh=False, only=None, discover=False, perf=False, rescore_only=False):
    con = sqlite3.connect(config.DB_PATH)
    init(con)
    if rescore_only:
        rescore(con)
        return
    rows = due_rows(con, refresh, only)
    if only and not rows:
        sys.exit(f"No place with id {only}")
    print(f"Auditing {len(rows)} places")
    statuses = {}
    with httpx.Client() as client:
        for i, (pid, url, name, phone, source) in enumerate(rows, 1):
            url = normalize_url(url)
            print(f"[{i}/{len(rows)}] {url or '(no website)'}")
            kind, status = audit_one(con, client, pid, url, name, phone, source)
            if status:
                statuses[status] = statuses.get(status, 0) + 1
            if kind == "website":
                time.sleep(config.REQUEST_DELAY_S)
        print("Audit complete. URL checks:", statuses or "none needed")
        if discover and not only:
            run_discovery(con, client)
        if perf:
            fill_pagespeed(con, client)


if __name__ == "__main__":
    args = sys.argv[1:]
    only = None
    if "--only" in args:
        if args.index("--only") + 1 >= len(args):
            sys.exit(__doc__)
        only = args[args.index("--only") + 1]
    main(refresh="--refresh" in args, only=only, discover="--discover" in args,
         perf="--perf" in args, rescore_only="--rescore" in args)
