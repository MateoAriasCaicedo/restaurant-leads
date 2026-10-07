"""Shared SQLite + folder helpers for the per-lead pipeline (approve.py, enrich.py, score.py)."""
import re
import sqlite3
import time
import unicodedata
from pathlib import Path

from leadgen import config

STATUSES = ("approved", "enriched", "ready", "contacted", "rejected")
PHOTO_SOURCES = ("instagram", "maps")
# Outreach log (web app): how the restaurant was contacted and what came of it.
CHANNELS = ("whatsapp", "phone", "instagram", "email", "visit", "other")
OUTCOMES = ("no_answer", "talking", "interested", "meeting", "proposal_sent", "won", "not_interested", "opt_out")


def connect():
    con = sqlite3.connect(config.DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("CREATE TABLE IF NOT EXISTS lead_status (place_id TEXT PRIMARY KEY, status TEXT NOT NULL, updated_at REAL)")
    con.execute("""CREATE TABLE IF NOT EXISTS lead_profile (
        place_id TEXT PRIMARY KEY, profile_json TEXT, brief_path TEXT, models TEXT, created_at REAL)""")
    con.execute("CREATE TABLE IF NOT EXISTS lead_notes (place_id TEXT PRIMARY KEY, body TEXT, updated_at REAL)")
    con.execute("""CREATE TABLE IF NOT EXISTS lead_contacts (
        id INTEGER PRIMARY KEY, place_id TEXT NOT NULL, at REAL, channel TEXT, outcome TEXT, note TEXT, created_at REAL)""")
    return con


def set_status(con, place_id, status):
    con.execute("INSERT OR REPLACE INTO lead_status VALUES (?,?,?)", (place_id, status, time.time()))
    con.commit()


def clear_status(con, place_id):
    con.execute("DELETE FROM lead_status WHERE place_id=?", (place_id,))
    con.commit()


def get_status(con, place_id):
    r = con.execute("SELECT status FROM lead_status WHERE place_id=?", (place_id,)).fetchone()
    return r["status"] if r else None


def _norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def slug(name, place_id):
    return f"{_norm(name).replace(' ', '-')[:40] or 'lead'}-{place_id.split('/')[-1]}"


def key(place_id):
    """URL-safe form of a place_id: osm:node/123 -> osm-node-123."""
    return place_id.replace(":", "-").replace("/", "-")


def by_key(con, k):
    """The place for a key() value, or None."""
    m = re.fullmatch(r"([a-z]+)-([a-z]+)-(\d+)", k or "")
    if not m:
        return None
    return con.execute("SELECT * FROM places WHERE place_id=?", (f"{m[1]}:{m[2]}/{m[3]}",)).fetchone()


def find(con, term):
    """Places whose id equals `term` or whose accent-insensitive name contains it."""
    exact = con.execute("SELECT * FROM places WHERE place_id=?", (term,)).fetchall()
    if exact:
        return exact
    t = _norm(term)
    return [p for p in con.execute("SELECT * FROM places") if t and t in _norm(p["name"])]


def lead_dir(place, create=True):
    d = Path(config.LEADS_DIR) / slug(place["name"], place["place_id"])
    if create:
        for sub in [Path("raw"), Path("profile")] + [Path("photos") / s for s in PHOTO_SOURCES]:
            (d / sub).mkdir(parents=True, exist_ok=True)
    return d
