"""Per-lead market + presence research for enrich.py.

competitors(): free, computed from the other places already in leads.db.
presence():    Claude + server-side web search over public sources (TripAdvisor, delivery apps,
               Facebook/Instagram pages, news...). Returns structured findings with source URLs
               and an operating-status verdict. Nothing is scraped by this code.
"""
import json
import math
from datetime import date

from leadgen import config
from leadgen.enrichment import llm


def _dist_m(a_lat, a_lng, b_lat, b_lng):
    r = 6371000
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dp, dl = p2 - p1, math.radians(b_lng - a_lng)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def _cuisine(row):
    try:
        c = json.loads(row["tags_json"] or "{}").get("cuisine")
    except Exception:
        c = None
    return c.split(";")[0].strip().lower() if c else None


def competitors(con, place, radius=None):
    """Nearby restaurants (chains excluded) and how their web presence compares to this lead."""
    radius = radius or config.COMPETITOR_RADIUS_M
    if place["lat"] is None or place["lng"] is None:
        return {"radius_m": radius, "note": "lead has no coordinates"}
    audits = {r["place_id"]: r for r in con.execute("SELECT place_id, web_type, http_ok, web_score FROM audits")}
    mine = _cuisine(place)
    near = []
    for q in con.execute("SELECT * FROM places WHERE place_id != ? AND lat IS NOT NULL", (place["place_id"],)):
        if any(c in (q["name"] or "").lower() for c in config.CHAINS):
            continue
        d = _dist_m(place["lat"], place["lng"], q["lat"], q["lng"])
        if d <= radius:
            a = audits.get(q["place_id"])
            working = bool(a and a["web_type"] == "website" and a["http_ok"])
            near.append({"name": q["name"], "distance_m": round(d), "cuisine": _cuisine(q),
                         "web": "working website" if working else (a["web_type"] if a else "unknown"),
                         "web_score": a["web_score"] if a else None, "_working": working})
    near.sort(key=lambda x: x["distance_m"])
    same = [n for n in near if mine and n["cuisine"] == mine]
    n_work = sum(1 for n in near if n["_working"])
    out = {
        "radius_m": radius, "restaurants_nearby": len(near), "with_working_website": n_work,
        "without_working_website": len(near) - n_work, "lead_cuisine": mine,
        "same_cuisine_nearby": len(same),
        "same_cuisine_with_working_website": sum(1 for n in same if n["_working"]),
        "nearest": [{k: v for k, v in n.items() if k != "_working"} for n in (same or near)[:6]],
    }
    out["insight"] = (f"{n_work} of {len(near)} restaurants within {radius} m have a working website"
                      + (f"; {out['same_cuisine_with_working_website']} of {len(same)} serve the same cuisine ({mine})" if same else ""))
    return out


def presence(place, tags, site, notes, audit):
    web = (audit["final_url"] if audit and audit["http_ok"] else None) or "none known"
    socials = {k: v for k, v in tags.items() if any(s in k for s in ("instagram", "facebook", "website", "url", "whatsapp", "phone"))}
    info = (f"Name: {place['name']}\nCity: Medellín, Antioquia, Colombia (neighborhood/area: {place['area']})\n"
            f"Address: {place['address'] or 'unknown'}\nPhone: {place['phone'] or 'unknown'}\n"
            f"Website: {web}\nKnown handles/links from OpenStreetMap: {json.dumps(socials, ensure_ascii=False)}\n"
            f"Notes pasted by the user (e.g. Instagram bio/captions): {notes or '(none)'}")
    report, sources = llm.research_presence(info, date.today().isoformat())
    data = llm.extract_presence(report, sources)
    data["sources"] = sources
    data["report"] = report
    return data
