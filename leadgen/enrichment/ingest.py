"""Turn an analysis written by an LLM session (e.g. Claude Code) into the lead profile. No API key needed.

Workflow without an API key:
  python enrich.py --collect-only --only NAME    # writes leads/<slug>/context.md (+ schemas.json)
  ... the analysis is written to leads/<slug>/profile/profile.json (and optionally menu.json, presence.json, design_system.json) ...
  python ingest.py NAME                           # validates, records the profile, marks the lead 'enriched'
"""
import json
import re
import sys

from leadgen.enrichment import enrich
from leadgen.enrichment import llm
from leadgen import store


SCHEMAS = {"profile": llm.PROFILE_SCHEMA, "menu": llm.MENU_SCHEMA, "presence": llm.PRESENCE_SCHEMA,
           "design_system": llm.DESIGN_SYSTEM_SCHEMA}
_PRIMITIVES = {
    "string": lambda v: isinstance(v, str),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


def problems(value, schema, path="profile"):
    """Minimal check that required keys exist, enums match, string patterns hold and leaf types are right
    (enough to catch a malformed hand-written or model-written profile). Extra keys are allowed."""
    out = []
    t = schema.get("type")
    if t == "object" and isinstance(value, dict):
        for k in schema.get("required", []):
            if k not in value:
                out.append(f"{path}.{k} is missing")
        for k, sub in schema.get("properties", {}).items():
            if k in value:
                out += problems(value[k], sub, f"{path}.{k}")
    elif t == "array" and isinstance(value, list):
        for i, it in enumerate(value):
            out += problems(it, schema.get("items", {}), f"{path}[{i}]")
    elif t == "object" or t == "array":
        out.append(f"{path} should be a {t}")
    elif t:
        kinds = t if isinstance(t, list) else [t]
        if not any(_PRIMITIVES.get(k, lambda v: True)(value) for k in kinds):
            out.append(f"{path} should be {' or '.join(kinds)}, got {type(value).__name__}")
    if "enum" in schema and value not in schema["enum"]:
        out.append(f"{path} = {value!r} not in {schema['enum']}")
    if isinstance(value, str) and "pattern" in schema and not re.fullmatch(schema["pattern"], value):
        out.append(f"{path} = {value!r} does not match {schema['pattern']}")
    return out


def check_file(f, name):
    """(data, problems) for one analysis file; data is None when the file is missing or not JSON."""
    if not f.exists():
        return None, []
    try:
        data = json.loads(f.read_text("utf-8"))
    except ValueError as e:
        return None, [f"{name} is not valid JSON: {e}"]
    return data, problems(data, SCHEMAS[name], name)


def validate_dir(prof):
    """{name: [problems]} for profile/menu/presence/design_system.json in a profile folder. A missing profile.json is a
    problem; the others are optional."""
    out = {name: check_file(prof / f"{name}.json", name)[1] for name in SCHEMAS}
    if not (prof / "profile.json").exists():
        out["profile"] = ["profile.json not found"]
    return out


def load(prof, name, schema):
    f = prof / f"{name}.json"
    if not f.exists():
        return None
    data = json.loads(f.read_text("utf-8"))
    bad = problems(data, schema, name)
    if bad:
        sys.exit(f"{f} has problems:\n  " + "\n  ".join(bad[:15]))
    return data


def main(term):
    con = store.connect()
    found = store.find(con, term)
    if len(found) != 1:
        sys.exit("No match." if not found else "Ambiguous, use a place_id:\n" + "\n".join(f"  {p['place_id']}  {p['name']}" for p in found[:10]))
    p = found[0]
    d = store.lead_dir(p, create=False)
    prof = d / "profile"
    profile = load(prof, "profile", llm.PROFILE_SCHEMA)
    if profile is None:
        sys.exit(f"{prof / 'profile.json'} not found. Run enrich.py --collect-only first and write the analysis.")
    load(prof, "menu", llm.MENU_SCHEMA)
    load(prof, "presence", llm.PRESENCE_SCHEMA)
    load(prof, "design_system", llm.DESIGN_SYSTEM_SCHEMA)
    missing = [s for s in store.PHOTO_SOURCES if not enrich.photo_files(d, s)]
    print(f"[{p['name']}]")
    enrich.finish(con, p, profile, missing, {"analysis": "claude-code session (no API)"})


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
