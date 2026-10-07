"""Compute Sell Score (0-100), tiers, and export ranked leads to CSV.

Works with two data shapes:
  - rich data (rating + review count present): original scoring
  - OpenStreetMap data (no ratings): scoring from completeness/activity proxies

Usage: python score.py [output.csv]   (default: data/exports/leads_ranked.csv)
"""
import csv
import json
import sqlite3
import sys
from datetime import datetime, timezone

from leadgen import config
from leadgen.scoring import quality

COMPLAINT_WORDS = ("menú", "menu", "horario", "reserva", "no contestan", "no responden", "teléfono", "telefono", "pagina", "página")

# Tier cut-offs used when ratings are unavailable (OSM data is sparser)
OSM_TIER_A = 70
OSM_TIER_B = 50


def tags_of(p):
    try:
        return json.loads(p["tags_json"] or "{}")
    except Exception:
        return {}


def excluded(p, maps=None):
    """Why a place is left out of the ranking, or None. `maps` is its place_quality row (scraped Maps listing), if any."""
    name = (p["name"] or "").lower()
    t = tags_of(p)
    if p["status"] and p["status"] != "OPERATIONAL":
        return "not operational"
    if maps and maps["closed_flag"] == "permanently closed":
        return "permanently closed"
    if any(c in name for c in config.CHAINS) or t.get("brand") or t.get("brand:wikidata"):
        return "chain"
    types = set(json.loads(p["types"] or "[]"))
    if types & config.EXCLUDED_TYPES:
        return "hotel/mall/other"
    if p["review_count"] is not None and p["review_count"] < config.MIN_REVIEWS:
        return "too few reviews"
    return None


def recent_reviews(reviews, days=120):
    n, complaints = 0, 0
    now = datetime.now(timezone.utc)
    for r in reviews:
        try:
            t = datetime.fromisoformat(r["publishTime"].replace("Z", "+00:00"))
            if (now - t).days <= days:
                n += 1
        except Exception:
            pass
        text = (r.get("text") or {}).get("text", "").lower()
        if r.get("rating", 5) <= 3 and any(w in text for w in COMPLAINT_WORDS):
            complaints += 1
    return n, complaints


def check_date_recent(t, months=24):
    cd = t.get("check_date") or t.get("survey:date")
    if not cd:
        return False
    try:
        d = datetime.fromisoformat(cd[:10]).replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - d).days <= months * 30
    except Exception:
        return False


def score(p, a, uc=None):
    w = config.WEIGHTS
    reasons = []
    t = tags_of(p)
    rich = p["rating"] is not None and p["review_count"] is not None

    # NEED (0-30): inverse of website quality
    web_type = a["web_type"] if a else "none"
    ws = a["web_score"] if a else 0
    need = w["need"] * (1 - ws / 100)
    if web_type == "none":
        need = w["need"]
        reasons.append("no website")
    elif web_type == "social_only":
        need = w["need"] * 0.95
        reasons.append("only social/delivery page, no website")
    elif ws >= 75:
        need = 0

    if uc and uc["status"] in ("dead", "unreachable", "parked"):
        need = w["need"]          # their listed site does not work: as good as no website
        reasons.append(f"website link is broken ({uc['note']})")
    elif uc and uc["status"] == "ok" and uc["name_match"] == 0:
        # the page loads but never mentions the restaurant: likely a wrong link, so its quality says little
        need = max(need, w["need"] * 0.6)
        reasons.append("listed website may belong to another business")

    # an audit that could not be verified (e.g. "no website" that is only absent from OSM) counts for less
    conf = a["confidence"] if a and "confidence" in a.keys() else None
    factor = config.CONFIDENCE_NEED_FACTOR.get(conf, 1.0)
    if factor < 1 and web_type == "none":
        reasons = [r + " (unverified)" if r == "no website" else r for r in reasons]
    need *= factor

    social = bool(t.get("contact:instagram") or t.get("contact:facebook") or t.get("instagram") or t.get("facebook")
                  or (web_type == "social_only"))

    if rich:
        rc = p["review_count"] or 0
        ab = 12 * min(rc / 300, 1) + 8 * max(0, min(((p["rating"] or 0) - 3.8) / 0.8, 1))
        ab += {"PRICE_LEVEL_INEXPENSIVE": 3, "PRICE_LEVEL_MODERATE": 7, "PRICE_LEVEL_EXPENSIVE": 10,
               "PRICE_LEVEL_VERY_EXPENSIVE": 10}.get(p["price_level"], 5)
        ab = min(ab, w["ability"])
        if rc >= 150: reasons.append(f"{rc} reviews")
        if (p["rating"] or 0) >= 4.3: reasons.append(f"{p['rating']}★")
        reviews = json.loads(p["reviews_json"] or "[]")
        recent, complaints = recent_reviews(reviews)
        mom = min(recent, 4) * 3 + (4 if p["has_hours"] else 0) + min(complaints, 2) * 2
        mom = min(mom, w["momentum"])
        if recent >= 2: reasons.append(f"{recent} recent reviews (active)")
        if complaints: reasons.append("customers complain about menu/hours/contact")
    else:
        # OSM proxies: a well-described place is an established, invested business
        ab = 0
        if p["has_hours"]: ab += 8
        if t.get("cuisine"): ab += 6; reasons.append(f"cuisine: {t['cuisine'].split(';')[0]}")
        ab += min(2 * sum(1 for k in ("outdoor_seating", "takeaway", "delivery", "reservation", "internet_access", "air_conditioning")
                          if t.get(k) in ("yes", "only")), 8)
        if p["address"]: ab += 8
        ab = min(ab, w["ability"])
        mom = 0
        if social: mom += 12; reasons.append("active on social media")
        if check_date_recent(t): mom += 5
        if t.get("opening_hours"): mom += 3
        mom = min(mom, w["momentum"])

    reach = 0
    if p["phone"]: reach += 12; reasons.append("public phone")
    if t.get("contact:whatsapp") or (a and a["has_whatsapp"]): reach += 4; reasons.append("WhatsApp listed")
    if t.get("email") or t.get("contact:email"): reach += 4; reasons.append("public email")
    if p["maps_url"]: reach += 4
    reach = min(reach, w["reach"])

    total = round(need + ab + mom + reach)
    if need == 0:
        total = min(total, 45)
    if p["price_level"] and p["price_level"] not in config.TARGET_PRICE_LEVELS:
        total = round(total * 0.8)
    ta, tb = (config.TIER_A, config.TIER_B) if rich else (OSM_TIER_A, OSM_TIER_B)
    tier = "A" if total >= ta else "B" if total >= tb else "C"
    # present the most useful reasons first
    reasons.sort(key=lambda r: 0 if r.startswith(("no website", "only social", "website link", "listed website")) else 1)
    return total, tier, round(need), round(ab), round(mom), round(reach), reasons


def dedupe(rows, skipped, hidden=None):
    """OSM can list one restaurant as both a node and a way. Keep the best-scored copy
    (rows arrive sorted best-first) when same normalized name and ~100 m apart.
    Dropped copies are appended to `hidden` (if given) with excluded_reason 'duplicate'."""
    kept, by_key = [], {}
    for r in rows:
        key = "".join(ch for ch in (r["name"] or "").lower() if ch.isalnum())
        dup = any(abs(k["_lat"] - r["_lat"]) < 0.001 and abs(k["_lng"] - r["_lng"]) < 0.001
                  for k in by_key.get(key, ()))
        if dup:
            skipped["duplicate"] = skipped.get("duplicate", 0) + 1
            if hidden is not None:
                r["excluded_reason"] = "duplicate"
                hidden.append(r)
            continue
        by_key.setdefault(key, []).append(r)
        kept.append(r)
    for r in kept + (hidden or []):
        r.pop("_lat", None); r.pop("_lng", None)
    return kept


# Columns of the exported CSV, in order. Rows from ranked() carry these plus a few extras for the web app.
CSV_FIELDS = ["tier", "sell_score", "name", "area", "phone", "address", "rating", "reviews", "price",
              "web_status", "web_score", "confidence", "website", "url_status", "url_note", "top_issues", "why_a_fit",
              "need", "ability", "momentum", "reach", "map_link", "status", "operating_status", "quality", "quality_tier", "place_id"]


def load_context(con):
    """Per-place lookups used to build rows. Tables that do not exist yet count as empty."""
    def table(sql, value):
        try:
            return {r[0]: value(r) for r in con.execute(sql)}
        except sqlite3.OperationalError:
            return {}
    return {
        "audits": table("SELECT * FROM audits", lambda r: r),
        "statuses": table("SELECT place_id, status FROM lead_status", lambda r: r[1]),
        "urlchecks": table("SELECT * FROM url_checks", lambda r: r),
        "quality": quality.load(con),
        "op_status": table("SELECT place_id, profile_json FROM lead_profile",
                           lambda r: (json.loads(r[1]).get("operating_status") or {}).get("verdict", "")),
    }


def build_row(p, ctx):
    a = ctx["audits"].get(p["place_id"])
    uc = ctx["urlchecks"].get(p["place_id"])
    total, tier, n, ab, m, r, reasons = score(p, a, uc)
    mq = ctx["quality"].get(p["place_id"])
    qual = quality.evaluate(p, tags_of(p), mq)
    issues = (a["issues"] if a else "not audited") or ""
    return {
        "tier": tier, "sell_score": total, "name": p["name"], "area": p["area"],
        "phone": p["phone"], "address": p["address"], "rating": p["rating"] if p["rating"] is not None else (mq["rating"] if mq else None),
        "reviews": p["review_count"] if p["review_count"] is not None else (mq["review_count"] if mq else None), "price": (p["price_level"] or "").replace("PRICE_LEVEL_", ""),
        "web_status": a["web_type"] if a else "unknown", "web_score": a["web_score"] if a else "",
        "confidence": (a["confidence"] if a and "confidence" in a.keys() else None) or "",
        "evidence": (a["evidence"] if a and "evidence" in a.keys() else None) or "",
        "website": (a["final_url"] if a and "url_source" in a.keys() and a["url_source"] == "discovered" else None)
                   or p["website"] or "", "url_status": uc["status"] if uc else "",
        "url_note": (uc["note"] or "") if uc else "", "top_issues": "; ".join(issues.split("; ")[:3]),
        "why_a_fit": "; ".join(reasons[:4]), "need": n, "ability": ab, "momentum": m, "reach": r,
        "map_link": p["maps_url"], "status": ctx["statuses"].get(p["place_id"], ""),
        "operating_status": ctx["op_status"].get(p["place_id"], ""), "place_id": p["place_id"],
        # extras (not exported)
        "reasons": reasons, "issues": [i for i in issues.split("; ") if i] if a else [],
        "quality": qual["score"], "quality_tier": qual["tier"], "quality_source": qual["source"],
        "quality_reasons": qual["reasons"], "audited": bool(a), "cuisine": (tags_of(p).get("cuisine") or "").split(";")[0].strip(),
        "_lat": p["lat"] or 0, "_lng": p["lng"] or 0,
    }


def ranked(con, include_excluded=False):
    """Scored leads, best first, as (rows, skipped, hidden). `con` needs row_factory=sqlite3.Row.
    `skipped` counts what was left out by reason; `hidden` holds those rows (each with an
    `excluded_reason`) when include_excluded is set, so a UI can still show them."""
    ctx = load_context(con)
    rows, skipped, hidden = [], {}, []
    for p in con.execute("SELECT * FROM places"):
        why = excluded(p, ctx["quality"].get(p["place_id"]))
        if why:
            skipped[why] = skipped.get(why, 0) + 1
            if include_excluded:
                row = build_row(p, ctx)
                row.pop("_lat"); row.pop("_lng")
                row["excluded_reason"] = why
                hidden.append(row)
            continue
        rows.append(build_row(p, ctx))
    rows.sort(key=lambda x: -x["sell_score"])
    rows = dedupe(rows, skipped, hidden if include_excluded else None)
    return rows, skipped, hidden


def write_csv(rows, f):
    wr = csv.DictWriter(f, fieldnames=CSV_FIELDS if rows else ["empty"], extrasaction="ignore")
    wr.writeheader()
    wr.writerows(rows)


def main(out_path):
    con = sqlite3.connect(config.DB_PATH)
    con.row_factory = sqlite3.Row
    rows, skipped, _ = ranked(con)
    try:
        f = open(out_path, "w", newline="", encoding="utf-8-sig")
    except PermissionError:
        sys.exit(f"Cannot write {out_path}: it is probably open in Excel/Sheets. Close it and re-run, or pass another filename.")
    with f:
        write_csv(rows, f)
    tiers = {t: sum(1 for r in rows if r["tier"] == t) for t in "ABC"}
    print(f"Wrote {len(rows)} leads to {out_path}. Tiers: {tiers}. Excluded: {skipped}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else f"{config.EXPORTS_DIR}/leads_ranked.csv")
