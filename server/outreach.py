"""Outreach tracking: one private note per lead and a log of contacts.

The private note lives only in the database. It is never written into the lead folder, so it is never
part of what the analysis reads (unlike notes.txt, which is analysis input).
"""
import time

from leadgen import store


class Invalid(Exception):
    pass


def get_note(con, place_id):
    r = con.execute("SELECT body, updated_at FROM lead_notes WHERE place_id=?", (place_id,)).fetchone()
    return {"body": r["body"] or "", "updated_at": r["updated_at"]} if r else {"body": "", "updated_at": None}


def set_note(con, place_id, body):
    con.execute("INSERT OR REPLACE INTO lead_notes VALUES (?,?,?)", (place_id, str(body)[:20000], time.time()))
    con.commit()
    return get_note(con, place_id)


def contacts(con, place_id):
    return [dict(r) for r in con.execute(
        "SELECT id, at, channel, outcome, note, created_at FROM lead_contacts WHERE place_id=? ORDER BY at DESC, id DESC",
        (place_id,))]


def last_contacts(con):
    """{place_id: {at, channel, outcome, count}} for the list view."""
    out = {}
    for r in con.execute("SELECT place_id, at, channel, outcome FROM lead_contacts ORDER BY at, id"):
        n = out.get(r["place_id"], {}).get("count", 0)
        out[r["place_id"]] = {"at": r["at"], "channel": r["channel"], "outcome": r["outcome"], "count": n + 1}
    return out


def _clean(data, partial=False):
    out = {}
    if "channel" in data or not partial:
        if data.get("channel") not in store.CHANNELS:
            raise Invalid(f"channel must be one of: {', '.join(store.CHANNELS)}")
        out["channel"] = data["channel"]
    if "outcome" in data or not partial:
        if data.get("outcome") not in store.OUTCOMES:
            raise Invalid(f"outcome must be one of: {', '.join(store.OUTCOMES)}")
        out["outcome"] = data["outcome"]
    if "at" in data or not partial:
        at = data.get("at") or time.time()
        if not isinstance(at, (int, float)) or isinstance(at, bool) or not 0 < at < 4e9:
            raise Invalid("at must be a unix timestamp in seconds")
        out["at"] = float(at)
    if "note" in data or not partial:
        out["note"] = str(data.get("note") or "")[:5000]
    return out


def add_contact(con, place_id, data):
    """Log a contact. Logging one marks the lead contacted; an opt-out marks it rejected (Ley 1581: stop contacting)."""
    c = _clean(data)
    con.execute("INSERT INTO lead_contacts (place_id, at, channel, outcome, note, created_at) VALUES (?,?,?,?,?,?)",
                (place_id, c["at"], c["channel"], c["outcome"], c["note"], time.time()))
    con.commit()
    current = store.get_status(con, place_id)
    if c["outcome"] == "opt_out":
        store.set_status(con, place_id, "rejected")
    elif current != "rejected":
        store.set_status(con, place_id, "contacted")
    return store.get_status(con, place_id)


def update_contact(con, contact_id, data):
    c = _clean(data, partial=True)
    if c:
        con.execute(f"UPDATE lead_contacts SET {', '.join(k + '=?' for k in c)} WHERE id=?", (*c.values(), contact_id))
        con.commit()
    return con.execute("SELECT * FROM lead_contacts WHERE id=?", (contact_id,)).fetchone()


def delete_contact(con, contact_id):
    r = con.execute("SELECT place_id FROM lead_contacts WHERE id=?", (contact_id,)).fetchone()
    con.execute("DELETE FROM lead_contacts WHERE id=?", (contact_id,))
    con.commit()
    return r["place_id"] if r else None
