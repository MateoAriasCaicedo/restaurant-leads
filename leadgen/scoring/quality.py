"""Premium lead generation: a quality score (0-100) for high-end restaurants, kept apart from the Sell Score.

Two evidence levels:
  - OSM tags only (free, every place): a rough proxy, capped at OSM_CAP so it can only make a *candidate*.
  - Google Maps rating + review count (opt-in scrape.py, one lead at a time): confirms a *premium* lead.
The Maps numbers live in table `place_quality`, filled by `record()` (called from scrape.collect) or `backfill()`.

Usage:
  python quality.py                      # list premium leads and the best unverified candidates
  python quality.py --scrape 10 [--area poblado]   # scrape Maps for the 10 best candidates still without it
  python quality.py --backfill           # read existing leads/*/profile/scrape.json into place_quality
  python quality.py --csv data/exports/leads_premium.csv
"""
import argparse
import csv
import json
import math
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from leadgen import config
from leadgen import store

FINE_CUISINES = ("fine_dining", "french", "japanese", "sushi", "steak_house", "seafood", "wine", "tapas",
                 "mediterranean", "fusion", "contemporary", "peruvian", "spanish", "gourmet")
OSM_CAP = 60                 # OSM-only evidence never reaches PREMIUM_MIN
MAPS_OSM_SHARE = 20          # of the 100 points, at most this many come from OSM tags once Maps data exists


def ensure_table(con):
    con.execute("""CREATE TABLE IF NOT EXISTS place_quality (
        place_id TEXT PRIMARY KEY, rating REAL, review_count INTEGER, category TEXT,
        closed_flag TEXT, source TEXT, fetched_at REAL)""")


def _clip(x):
    return max(0.0, min(1.0, x))


def osm_points(p, tags):
    """(points, reasons) from OSM tags and the area. Uncapped sum; callers cap it."""
    pts, why = 0, []

    def add(n, reason=None):
        nonlocal pts
        pts += n
        if reason:
            why.append(reason)

    if tags.get("stars") or tags.get("michelin") or tags.get("award"):
        add(12, "star/award tag")
    if tags.get("wikidata") or tags.get("wikipedia"):
        add(8, "notable (Wikidata)")
    if tags.get("dress_code") in ("smart", "formal", "smart_casual"):
        add(8, f"dress code: {tags['dress_code']}")
    if tags.get("reservation") in ("yes", "required", "recommended"):
        add(6, "takes reservations")
    cuisines = {c.strip().lower() for c in (tags.get("cuisine") or "").split(";")}
    fine = cuisines & set(FINE_CUISINES)
    if fine:
        add(5, f"cuisine: {sorted(fine)[0].replace('_', ' ')}")
    if tags.get("drink:wine") in ("yes", "served") or tags.get("wine") == "yes":
        add(4, "wine list")
    if tags.get("description"):
        add(3)
    if tags.get("outdoor_seating") == "yes":
        add(2)
    if tags.get("air_conditioning") == "yes":
        add(2)
    if tags.get("payment:credit_cards") == "yes":
        add(2)
    if tags.get("opening_hours"):
        add(3)
    if p["website"]:
        add(3)
    if p["address"]:
        add(2)
    try:
        if int(tags.get("capacity") or 0) >= 50:
            add(2)
    except ValueError:
        pass
    bonus = config.PREMIUM_AREA_BONUS.get(p["area"], 0)
    if bonus:
        add(bonus, "upscale area")
    return pts, why


def evaluate(p, tags, maps=None):
    """Quality for one place. `maps` is a place_quality row (or dict) or None.
    Returns {"score", "tier" ('premium'|'candidate'|''), "source" ('maps'|'osm'), "reasons"}."""
    raw, why = osm_points(p, tags)
    if maps and maps["rating"] is not None and not maps["closed_flag"]:
        rc = maps["review_count"] or 0
        rating_pts = 55 * _clip((maps["rating"] - 4.0) / 0.8)
        review_pts = 25 * _clip(math.log10(max(rc, 1) / 50) / math.log10(20))
        score = round(rating_pts + review_pts + min(raw, MAPS_OSM_SHARE))
        why = [f"{maps['rating']}★ on Maps ({rc} reviews)"] + why
        ok = maps["rating"] >= config.PREMIUM_MIN_RATING and rc >= config.PREMIUM_MIN_REVIEWS
        tier = "premium" if ok and score >= config.PREMIUM_MIN else ""
        return {"score": score, "tier": tier, "source": "maps", "reasons": why}
    score = min(raw, OSM_CAP)
    tier = "candidate" if score >= config.CANDIDATE_MIN else ""
    return {"score": score, "tier": tier, "source": "osm", "reasons": why}


def load(con):
    """place_id -> place_quality row. A DB without the table counts as empty."""
    try:
        return {r["place_id"]: r for r in con.execute("SELECT * FROM place_quality")}
    except sqlite3.OperationalError:
        return {}


def record(con, place_id, maps):
    """Store a scrape_maps() result. Only a verified listing (name matched) with a rating or a closed flag is kept."""
    if not maps or maps.get("status") != "ok" or not maps.get("name_match") or (maps.get("rating") is None and not maps.get("closed_flag")):
        return False
    ensure_table(con)
    con.execute("INSERT OR REPLACE INTO place_quality VALUES (?,?,?,?,?,?,?)",
                (place_id, maps["rating"], maps.get("review_count"), maps.get("category"),
                 maps.get("closed_flag"), "maps", time.time()))
    con.commit()
    return True


def backfill(con):
    """Pick up Maps data from scrape.json files written before place_quality existed."""
    n = 0
    for p in con.execute("SELECT * FROM places"):
        f = store.lead_dir(p, create=False) / "profile" / "scrape.json"
        try:
            maps = json.loads(f.read_text("utf-8")).get("maps")
        except (OSError, ValueError):
            continue
        n += record(con, p["place_id"], maps)
    return n


def leads(con, area=None):
    """Every non-excluded place with its quality, best first: [(place, quality_dict)]."""
    from leadgen.scoring import score as sc
    q = load(con)
    out = []
    for p in con.execute("SELECT * FROM places"):
        if sc.excluded(p) or (area and p["area"] != area):
            continue
        out.append((p, evaluate(p, sc.tags_of(p), q.get(p["place_id"]))))
    out.sort(key=lambda x: -x[1]["score"])
    return out


def _print(rows, title):
    print(f"\n{title}")
    for p, q in rows:
        print(f"  {q['score']:3d} {q['source']:4s} {p['name'][:34]:34s} {p['area']:10s} {'; '.join(q['reasons'][:3])}")


def scrape_top(con, n, area=None, headed=False):
    from leadgen.enrichment import scrape
    if not scrape.installed():
        sys.exit("Playwright is not installed: pip install playwright && python -m playwright install chromium")
    todo = [(p, q) for p, q in leads(con, area) if q["source"] == "osm"][:n]
    if not todo:
        print("Every place already has Maps data; discover more places first.")
        return
    for p, q in todo:
        print(f"[{p['name']}] OSM quality {q['score']}")
        d = store.lead_dir(p)
        site = {}
        res = scrape.collect(p, json.loads(p["tags_json"] or "{}"), site, d, ("maps",), headed)   # records via record()
        m = res.get("maps", {})
        print("   ->", f"{m.get('rating')}★ / {m.get('review_count')}" if m.get("status") == "ok" else m.get("status"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scrape", type=int, metavar="N", help="scrape Maps for the N best unverified candidates")
    ap.add_argument("--area", choices=list(config.ALL_AREAS))
    ap.add_argument("--backfill", action="store_true")
    ap.add_argument("--csv", metavar="FILE")
    ap.add_argument("--headed", action="store_true")
    a = ap.parse_args()
    con = store.connect()
    ensure_table(con)
    if a.backfill:
        print(f"Recorded Maps data for {backfill(con)} leads.")
    if a.scrape:
        scrape_top(con, a.scrape, a.area, a.headed)
    rows = leads(con, a.area)
    prem = [r for r in rows if r[1]["tier"] == "premium"]
    cand = [r for r in rows if r[1]["tier"] == "candidate"]
    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8-sig") as f:
            wr = csv.writer(f)
            wr.writerow(["tier", "quality", "source", "name", "area", "phone", "address", "website", "why", "place_id"])
            for p, q in prem + cand:
                wr.writerow([q["tier"], q["score"], q["source"], p["name"], p["area"], p["phone"], p["address"],
                             p["website"], "; ".join(q["reasons"]), p["place_id"]])
        print(f"Wrote {len(prem) + len(cand)} rows to {a.csv}")
    _print(prem[:25], f"Premium (Maps-verified): {len(prem)}")
    _print(cand[:25], f"Candidates (OSM only, verify with --scrape): {len(cand)}")


if __name__ == "__main__":
    main()
