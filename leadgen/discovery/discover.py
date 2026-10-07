"""Discover restaurants from OpenStreetMap (Overpass API). Free, no account or key.

Usage: python discover.py [area ...]
Stores results in SQLite (table: places), deduped by OSM id.
OSM has no ratings or review counts, so score.py uses other proxies.
"""
import json
import sqlite3
import sys
import time

import httpx

from leadgen import config

MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]


def db():
    con = sqlite3.connect(config.DB_PATH)
    con.execute(
        """CREATE TABLE IF NOT EXISTS places (
            place_id TEXT PRIMARY KEY, area TEXT, name TEXT, address TEXT,
            lat REAL, lng REAL, rating REAL, review_count INTEGER,
            price_level TEXT, website TEXT, phone TEXT, status TEXT,
            primary_type TEXT, types TEXT, maps_url TEXT, reviews_json TEXT,
            has_hours INTEGER, fetched_at REAL, tags_json TEXT)"""
    )
    return con


def query(lat, lng, radius):
    return f"""[out:json][timeout:90];
(
  nwr["amenity"="restaurant"](around:{radius},{lat},{lng});
);
out tags center;"""


def fetch(client, q):
    for attempt in range(2):
        for url in MIRRORS:
            try:
                r = client.post(url, data={"data": q}, timeout=120,
                                headers={"User-Agent": config.USER_AGENT})
                if r.status_code == 200:
                    return r.json().get("elements", [])
                print("  mirror", url, "->", r.status_code)
            except Exception as e:
                print("  mirror", url, "failed:", type(e).__name__)
            time.sleep(3)
        time.sleep(15)
    return []


def first(tags, *keys):
    for k in keys:
        v = tags.get(k)
        if v:
            return v.strip()
    return None


def to_row(area, el):
    t = el.get("tags", {})
    name = t.get("name")
    if not name:
        return None
    lat = el.get("lat") or el.get("center", {}).get("lat")
    lng = el.get("lon") or el.get("center", {}).get("lon")
    site = first(t, "website", "contact:website", "url", "contact:url", "website:official")
    social = first(t, "contact:instagram", "contact:facebook", "facebook", "instagram")
    if not site and social:
        # keep social link so audit classifies it as "social_only"
        if social.startswith("http"):
            site = social
        else:
            site = "https://instagram.com/" + social.lstrip("@/")
    phone = first(t, "phone", "contact:phone", "contact:mobile", "mobile")
    addr = " ".join(x for x in [t.get("addr:street"), t.get("addr:housenumber"),
                                t.get("addr:suburb") or t.get("addr:neighbourhood"),
                                t.get("addr:city")] if x) or None
    pid = f"osm:{el['type']}/{el['id']}"
    return (
        pid, area, name, addr, lat, lng, None, None, None, site, phone, "OPERATIONAL",
        "restaurant", json.dumps(["restaurant"]),
        f"https://www.openstreetmap.org/{el['type']}/{el['id']}", "[]",
        1 if t.get("opening_hours") else 0, time.time(), json.dumps(t, ensure_ascii=False),
    )


def discover_area(con, client, area):
    """Fetch one area (a key of config.ALL_AREAS) and store it. Returns places saved, or None if nothing came back."""
    lat, lng, radius = config.ALL_AREAS[area]
    print(f"[{area}] querying OpenStreetMap...")
    elements = fetch(client, query(lat, lng, radius))
    if not elements:
        print(f"[{area}] WARNING: no data returned (all mirrors failed or area empty); skipping")
        return None
    n = 0
    for el in elements:
        row = to_row(area, el)
        if row:
            con.execute("INSERT OR REPLACE INTO places VALUES (" + ",".join("?" * 19) + ")", row)
            n += 1
    con.commit()
    print(f"[{area}] {n} named restaurants saved")
    return n


def main(areas):
    unknown = [a for a in areas if a not in config.ALL_AREAS]
    if unknown:
        sys.exit(f"Unknown area: {', '.join(unknown)}. Known areas: {', '.join(config.ALL_AREAS)}")
    con = db()
    total, failed = 0, []
    with httpx.Client() as client:
        for area in areas:
            n = discover_area(con, client, area)
            if n is None:
                failed.append(area)
                continue
            total += n
            time.sleep(5)
    print("Done. Total:", total)
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:] or list(config.AREAS))
