"""Manage lead status for the enrichment pipeline.

Usage:
  python approve.py list [status]
  python approve.py <status> <name-or-place_id> [...]    status: approved|enriched|ready|contacted|rejected

Approving creates leads/<slug>/photos/{instagram,maps}/ - drop screenshots/photos there
(and optionally a notes.txt with a pasted Instagram bio/captions) before running enrich.py.
"""
import sys

from leadgen import store


def main(argv):
    if not argv:
        print(__doc__)
        return
    con = store.connect()
    cmd = {"approve": "approved", "reject": "rejected"}.get(argv[0], argv[0])
    if cmd == "list":
        q = "SELECT s.status, p.place_id, p.name, p.area FROM lead_status s JOIN places p USING(place_id)"
        args = ()
        if len(argv) > 1:
            q += " WHERE s.status=?"
            args = (argv[1],)
        for r in con.execute(q + " ORDER BY s.status, p.name", args):
            print(f"{r['status']:10} {r['place_id']:24} {r['name']} ({r['area']})")
        return
    if cmd not in store.STATUSES:
        sys.exit(f"Unknown status '{cmd}'. Use one of: {', '.join(store.STATUSES)}")
    for term in argv[1:]:
        found = store.find(con, term)
        if len(found) != 1:
            print(f"'{term}': {'no match' if not found else 'ambiguous, use a place_id:'}")
            for p in found[:10]:
                print(f"    {p['place_id']}  {p['name']} ({p['area']})")
            continue
        p = found[0]
        store.set_status(con, p["place_id"], cmd)
        d = store.lead_dir(p) if cmd == "approved" else store.lead_dir(p, create=False)
        print(f"{p['name']} -> {cmd}   [{d}]")


if __name__ == "__main__":
    main(sys.argv[1:])
