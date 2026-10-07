"""Read models for the UI: the ranked list and one lead's full picture."""
import json
import math
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from leadgen.audit import audit
from leadgen import config
from leadgen.discovery import discover
from leadgen.enrichment import ingest
from leadgen.enrichment import research
from leadgen.enrichment import scrape
from leadgen.scoring import quality, score
from leadgen import store

from . import files, outreach, sitestack
from .jobs import manager


class NotFound(Exception):
    pass


def ensure_schema():
    """Create every table the app reads, so a fresh checkout shows an empty state instead of failing."""
    con = discover.db()
    audit.init(con)
    con.commit()
    con.close()
    store.connect().close()


@contextmanager
def db():
    con = store.connect()
    try:
        yield con
    finally:
        con.close()


def place_or_404(con, key):
    p = store.by_key(con, key)
    if p is None:
        raise NotFound(f"No lead with key {key}")
    return p


def _json(path):
    try:
        return json.loads(Path(path).read_text("utf-8"))
    except (OSError, ValueError):
        return None


def _tags(p):
    try:
        return json.loads(p["tags_json"] or "{}")
    except ValueError:
        return {}


def _reach(p, tags, a):
    return {
        "phone": bool(p["phone"]),
        "whatsapp": bool(tags.get("contact:whatsapp") or (a and a["has_whatsapp"])),
        "email": bool(tags.get("email") or tags.get("contact:email")),
        "social": bool(tags.get("contact:instagram") or tags.get("contact:facebook") or tags.get("instagram")
                       or tags.get("facebook") or (a and a["web_type"] == "social_only")),
    }


def list_leads(con, include_excluded=False):
    rows, skipped, hidden = score.ranked(con, include_excluded)
    places = {p["place_id"]: p for p in con.execute("SELECT * FROM places")}
    audits = {a["place_id"]: a for a in con.execute("SELECT place_id, has_whatsapp, web_type FROM audits")}
    profiled = {r[0] for r in con.execute("SELECT place_id FROM lead_profile")}
    last = outreach.last_contacts(con)
    for r in rows + hidden:
        p = places[r["place_id"]]
        r["key"] = store.key(r["place_id"])
        r["reach_flags"] = _reach(p, _tags(p), audits.get(r["place_id"]))
        r["has_profile"] = r["place_id"] in profiled
        r["last_contact"] = last.get(r["place_id"])
    return {
        "rows": rows, "hidden": hidden, "skipped": skipped,
        "counts": {"places": len(places), "scored": len(rows), "audited": sum(1 for r in rows if r["audited"]),
                   "profiled": sum(1 for r in rows if r["has_profile"]),
                   "tiers": {t: sum(1 for r in rows if r["tier"] == t) for t in "ABC"},
                   "premium": sum(1 for r in rows if r["quality_tier"] == "premium"),
                   "candidates": sum(1 for r in rows if r["quality_tier"] == "candidate")},
    }


def lead_detail(con, key):
    p = place_or_404(con, key)
    pid = p["place_id"]
    a = con.execute("SELECT * FROM audits WHERE place_id=?", (pid,)).fetchone()
    uc = con.execute("SELECT * FROM url_checks WHERE place_id=?", (pid,)).fetchone()
    total, tier, need, ability, momentum, reach, reasons = score.score(p, a, uc)
    rich = p["rating"] is not None and p["review_count"] is not None
    tags = _tags(p)
    d = store.lead_dir(p, create=False)
    prof = d / "profile"
    lp = con.execute("SELECT * FROM lead_profile WHERE place_id=?", (pid,)).fetchone()
    profile = _json(prof / "profile.json")
    if profile is None and lp:                         # folder moved or deleted: the DB still has the last profile
        try:
            profile = json.loads(lp["profile_json"])
        except ValueError:
            profile = None
    place = {k: p[k] for k in p.keys() if k not in ("tags_json", "reviews_json", "types")}
    job = manager.active(lead_key=key)
    return {
        "key": key, "slug": d.name, "place": place, "tags": tags,
        "excluded_reason": score.excluded(p, quality.load(con).get(pid)),
        "audit": dict(a) | {"issues": [i for i in (a["issues"] or "").split("; ") if i]} if a else None,
        "url_check": dict(uc) if uc else None,
        "score": {"total": total, "tier": tier, "need": need, "ability": ability, "momentum": momentum,
                  "reach": reach, "reasons": reasons, "weights": config.WEIGHTS, "rich": rich,
                  "tier_a": config.TIER_A if rich else score.OSM_TIER_A,
                  "tier_b": config.TIER_B if rich else score.OSM_TIER_B},
        "reach_flags": _reach(p, tags, a),
        "status": store.get_status(con, pid),
        "profile": sitestack.apply(profile),
        "profile_meta": {"created_at": lp["created_at"], "models": _safe_json(lp["models"])} if lp else None,
        "profile_problems": ingest.validate_dir(prof) if (prof / "profile.json").exists() else None,
        "menu": _json(prof / "menu.json"),
        "presence": _json(prof / "presence.json"),
        "design_system": _json(prof / "design_system.json"),
        "competitors": research.competitors(con, p),
        "block": block(con, p),
        "site": _site(_json(prof / "site.json")),
        "scrape": _json(prof / "scrape.json"),
        "files": {kind: files.listing(d, kind, key) for kind in files.KINDS},
        "notes_txt": (d / "notes.txt").read_text("utf-8", errors="replace") if (d / "notes.txt").exists() else "",
        "has_context": (d / "context.md").exists(),
        "private_note": outreach.get_note(con, pid),
        "contacts": outreach.contacts(con, pid),
        "active_job": job.public() if job else None,
    }


def block(con, p, radius=None):
    """The lead's surroundings as a plot: every other place within `radius` metres, positioned in metres
    east (dx) and north (dy) of the lead, with the state of its web presence."""
    radius = radius or config.COMPETITOR_RADIUS_M
    if p["lat"] is None or p["lng"] is None:
        return {"radius_m": radius, "points": None}
    audits = {r["place_id"]: r for r in con.execute("SELECT place_id, web_type, http_ok FROM audits")}
    mine = (_tags(p).get("cuisine") or "").split(";")[0].strip().lower()
    east = math.cos(math.radians(p["lat"])) * 111320          # metres per degree of longitude here
    points = []
    for q in con.execute("SELECT * FROM places WHERE place_id != ? AND lat IS NOT NULL AND lng IS NOT NULL", (p["place_id"],)):
        dx, dy = (q["lng"] - p["lng"]) * east, (q["lat"] - p["lat"]) * 110540
        dist = math.hypot(dx, dy)
        if dist > radius:
            continue
        a = audits.get(q["place_id"])
        if a is None:
            web = "unknown"
        elif a["web_type"] == "website":
            web = "working" if a["http_ok"] else "blocked" if a["http_ok"] is None else "broken"
        else:
            web = a["web_type"]                               # none | social_only
        cuisine = (_tags(q).get("cuisine") or "").split(";")[0].strip().lower()
        points.append({"key": store.key(q["place_id"]), "name": q["name"], "dx": round(dx), "dy": round(dy),
                       "distance_m": round(dist), "web": web, "cuisine": cuisine,
                       "same_cuisine": bool(mine and cuisine == mine), "chain": score.excluded(q) == "chain"})
    points.sort(key=lambda x: x["distance_m"])
    return {"radius_m": radius, "points": points}


def _safe_json(s):
    try:
        return json.loads(s or "null")
    except ValueError:
        return None


def _site(site):
    """What the own-site crawl found, without the page text (it is long, and already in context.md)."""
    if not site:
        return None
    return {"url": site.get("url"), "error": site.get("error"), "palette": site.get("palette") or [],
            "fonts": site.get("fonts") or [], "pages": [pg.get("url") for pg in site.get("pages") or []]}


def meta(con):
    from . import claude_cli
    counts = {r[0]: (r[1], r[2]) for r in con.execute(
        """SELECT p.area, COUNT(*), COUNT(a.place_id) FROM places p LEFT JOIN audits a USING(place_id) GROUP BY p.area""")}
    latest = {r[0]: r[1] for r in con.execute("SELECT area, MAX(fetched_at) FROM places GROUP BY area")}
    areas = [{"key": k, "lat": v[0], "lng": v[1], "radius_m": v[2], "default": k in config.DEFAULT_AREAS,
              "places": counts.get(k, (0, 0))[0], "audited": counts.get(k, (0, 0))[1], "fetched_at": latest.get(k)}
             for k, v in config.ALL_AREAS.items()]
    try:
        unaudited = con.execute("SELECT COUNT(*) FROM places p LEFT JOIN audits a USING(place_id) WHERE a.place_id IS NULL").fetchone()[0]
    except sqlite3.OperationalError:
        unaudited = 0
    try:
        verified = con.execute("SELECT COUNT(*) FROM place_quality").fetchone()[0]
    except sqlite3.OperationalError:
        verified = 0
    return {
        "app_name": config.APP_NAME, "maps_verified": verified,
        "statuses": store.STATUSES, "channels": store.CHANNELS, "outcomes": store.OUTCOMES,
        "areas": areas, "unaudited": unaudited, "weights": config.WEIGHTS,
        "tiers": {"osm": {"a": score.OSM_TIER_A, "b": score.OSM_TIER_B}, "rich": {"a": config.TIER_A, "b": config.TIER_B}},
        "limits": {"photos_per_source": config.MAX_PHOTOS_PER_SOURCE, "upload_mb": config.MAX_UPLOAD_MB,
                   "url_recheck_days": config.URL_RECHECK_DAYS, "competitor_radius_m": config.COMPETITOR_RADIUS_M},
        "scrape": {"available": scrape.installed()},
        "claude": {"available": bool(claude_cli.binary()), "version": claude_cli.version(), "model": config.CLAUDE_MODEL},
    }
