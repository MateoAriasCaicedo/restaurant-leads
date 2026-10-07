""""Get insights" for one lead, with no API key: collect -> headless Claude analysis -> validate -> ingest.

  prepare   mark the lead approved if it has no status (so the final step moves it to enriched)
  collect   python enrich.py --collect-only  (site crawl, competitors, context.md; no LLM)
  stage     copy that lead's public inputs into a disposable workspace, .runs/<id>/ws
  analyze   claude -p in the workspace (see claude_cli); it writes out/{profile,menu,presence,design_system}.json
  validate  size caps, JSON parse, schema check; one repair round if needed
  promote   back up the lead's current profile files, copy the new ones in
  ingest    python ingest.py  (records the profile; the backup is restored if this fails)

Nothing Claude writes is executed, and only the four fixed output files are ever read back.

`start_design` is the same job cut down to the design system: for a lead that is already researched it stages the
finished profile and photos, asks Claude for out/design_system.json alone (no web research), validates it and saves
it next to the profile. The profile, menu and presence are not touched, and nothing is re-ingested.
"""
import json
import shutil
from datetime import date
from pathlib import Path

from leadgen import config
from leadgen.enrichment import ingest, llm
from leadgen.enrichment import scrape as scrape_mod
from leadgen import store

from . import ROOT, claude_cli
from .jobs import Job, JobError, kill_tree, manager, python

STEPS = [("prepare", "Prepare"), ("collect", "Collect site, nearby data and public pages"), ("stage", "Set up workspace"),
         ("analyze", "Research and analysis"), ("validate", "Check the result"),
         ("promote", "Save the profile"), ("ingest", "Record the profile")]
DESIGN_STEPS = [("prepare", "Prepare"), ("stage", "Set up workspace"), ("analyze", "Write the design system"),
                ("validate", "Check the result"), ("promote", "Save the design system")]
OUTPUTS = ("profile", "menu", "presence", "design_system")
PROFILE_INPUTS = ("competitors.json", "site.json", "scrape.json")
DESIGN_INPUTS = ("profile.json", "menu.json", "presence.json", "site.json", "scrape.json")     # the finished analysis is an input here
MAX_OUTPUT_KB = 400
MAX_STAGED_FILE_MB = 20
PROMPTS = Path(__file__).parent / "prompts"
PROMPT = (PROMPTS / "analyze.md").read_text("utf-8")
DESIGN_PROMPT = (PROMPTS / "design.md").read_text("utf-8")
DESIGN_RULES = (PROMPTS / "design_rules.md").read_text("utf-8").rstrip("\n")        # shared by both prompts


def _fill(template, name, slug):
    return (template.replace("{design_rules}", DESIGN_RULES).replace("{today}", date.today().isoformat()).replace("{slug}", slug)
            .replace("{name}", name).replace("{stack}", config.SITE_STACK_TEXT))


def build_prompt(name, slug):
    return _fill(PROMPT, name, slug)


def build_design_prompt(name, slug):
    return _fill(DESIGN_PROMPT, name, slug)


def start(place, dry_run=False, scrape=False):
    """Start the job, or return None if another analysis is already running."""
    lead = {"key": store.key(place["place_id"]), "name": place["name"]}
    steps = STEPS[:5] if dry_run else STEPS
    job = Job("enrich", f"Get insights: {place['name']}", "enrich",
              {"place_id": place["place_id"], "dry_run": bool(dry_run), "scrape": bool(scrape)}, lead, steps)
    place = dict(place)                               # sqlite rows must not cross threads
    return manager.start_exclusive(job, lambda j: run(j, place, dry_run, scrape))


def start_design(place):
    """Start writing only the design system of an already researched lead, or return None if an analysis is running.
    It shares the enrich lane, so it never runs beside another analysis."""
    lead = {"key": store.key(place["place_id"]), "name": place["name"]}
    job = Job("enrich", f"Design system: {place['name']}", "enrich", {"place_id": place["place_id"], "mode": "design"}, lead, DESIGN_STEPS)
    place = dict(place)
    return manager.start_exclusive(job, lambda j: run_design(j, place))


def run(job, place, dry_run, scrape=False):
    pid = place["place_id"]
    d = store.lead_dir(place)                         # leads/<slug>, created if missing
    slug = d.name

    job.begin("prepare")
    if not claude_cli.binary():
        raise JobError("The Claude Code CLI (`claude`) was not found on PATH.")
    con = store.connect()
    try:
        if not dry_run and store.get_status(con, pid) is None:
            store.set_status(con, pid, "approved")
            job.log("Marked as approved.")
    finally:
        con.close()

    if scrape and not scrape_mod.installed():
        raise JobError("Scraping needs Playwright: pip install playwright && python -m playwright install chromium")

    job.begin("collect")
    if job.run_cmd(python("enrich.py", "--collect-only", "--refresh", *(["--scrape"] if scrape else []), "--only", pid)) != 0:
        raise JobError("Collecting the lead's data failed; see the log.")
    if not (d / "context.md").exists():
        raise JobError("Collecting produced no context.md.")

    job.begin("stage")
    ws = job.dir / "ws"
    n = stage(d, ws / "leads" / slug)
    (ws / "out").mkdir(parents=True, exist_ok=True)
    job.log(f"Workspace ready: {n} files copied.")

    job.begin("analyze")
    session = claude_run(job, ws, build_prompt(place["name"] or slug, slug))

    job.begin("validate")
    validate(job, ws, slug, session, check_outputs)
    produced = [n for n in OUTPUTS if (ws / "out" / f"{n}.json").exists()]
    job.log("Valid: " + ", ".join(f"{n}.json" for n in produced))
    job.result = {"files": produced, "draft_dir": (ws / "out").relative_to(ROOT).as_posix()}
    if dry_run:
        job.log("Dry run: the lead's saved profile was not changed.")
        return

    job.begin("promote")
    prof, prev = d / "profile", job.dir / "prev"
    prev.mkdir(parents=True, exist_ok=True)
    had = []
    for n in OUTPUTS:
        if (prof / f"{n}.json").exists():
            shutil.copy2(prof / f"{n}.json", prev / f"{n}.json")
            had.append(n)
    prof.mkdir(parents=True, exist_ok=True)
    for n in produced:
        shutil.copy2(ws / "out" / f"{n}.json", prof / f"{n}.json")
    job.log(f"Saved {len(produced)} files" + (f"; previous versions kept in {prev.relative_to(ROOT).as_posix()}" if had else ""))

    job.begin("ingest")
    if job.run_cmd(python("ingest.py", pid)) != 0:
        for n in produced:                            # put things back exactly as they were
            if n in had:
                shutil.copy2(prev / f"{n}.json", prof / f"{n}.json")
            else:
                (prof / f"{n}.json").replace(prev / f"rejected-{n}.json")
        raise JobError("Recording the profile failed; the previous profile was restored.")
    shutil.rmtree(ws, ignore_errors=True)             # the workspace was only a copy
    job.result.pop("draft_dir", None)


def run_design(job, place):
    d = store.lead_dir(place)
    slug = d.name

    job.begin("prepare")
    if not claude_cli.binary():
        raise JobError("The Claude Code CLI (`claude`) was not found on PATH.")
    if not (d / "profile" / "profile.json").exists():
        raise JobError("This lead has not been researched yet: the design system is written from its profile. Get insights first.")

    job.begin("stage")
    ws = job.dir / "ws"
    n = stage(d, ws / "leads" / slug, DESIGN_INPUTS)
    (ws / "leads" / slug / "schemas.json").write_text(json.dumps({"design_system": llm.DESIGN_SYSTEM_SCHEMA}, ensure_ascii=False, indent=1), "utf-8")
    (ws / "out").mkdir(parents=True, exist_ok=True)
    job.log(f"Workspace ready: {n} files copied.")

    job.begin("analyze")
    session = claude_run(job, ws, build_design_prompt(place["name"] or slug, slug))

    job.begin("validate")
    validate(job, ws, slug, session, check_design)
    job.log("Valid: design_system.json")
    job.result = {"files": ["design_system"]}

    job.begin("promote")
    target, prev = d / "profile" / "design_system.json", job.dir / "prev"
    had = target.exists()
    if had:
        prev.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, prev / "design_system.json")
    shutil.copy2(ws / "out" / "design_system.json", target)
    job.log("Saved design_system.json" + (f"; the previous one is kept in {prev.relative_to(ROOT).as_posix()}" if had else ""))
    shutil.rmtree(ws, ignore_errors=True)             # the workspace was only a copy


def validate(job, ws, slug, session, check):
    """Check what Claude wrote. On problems it gets one round to fix them (same session); after that the job fails."""
    bad = check(ws / "out")
    if bad:
        job.log("The result has problems; asking Claude to fix them:", "warn")
        for b in bad[:20]:
            job.log(f"  {b}", "warn")
        if not session:
            raise JobError("The analysis did not pass validation: " + "; ".join(bad[:5]))
        job.step = "analyze"
        claude_run(job, ws, "The files you wrote in out/ have these problems:\n- " + "\n- ".join(bad[:40]) +
                   "\n\nFix them by rewriting the affected files in out/. Follow leads/" + slug +
                   "/schemas.json exactly. Do no further research.", resume=session)
        job.step = "validate"
        bad = check(ws / "out")
        if bad:
            raise JobError("The analysis did not pass validation: " + "; ".join(bad[:5]))


def stage(src, dest, profile_inputs=PROFILE_INPUTS):
    """Copy the lead's analysis inputs (and nothing else) into the workspace. Returns the file count."""
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    n = 0
    if (src / "context.md").exists():
        ctx = (src / "context.md").read_text("utf-8")
        (dest / "context.md").write_text(ctx.split("## To finish this lead")[0].rstrip() + "\n", "utf-8")
        n += 1
    for name in ("schemas.json", "notes.txt"):
        if (src / name).exists():
            shutil.copy2(src / name, dest / name)
            n += 1
    for name in profile_inputs:
        if (src / "profile" / name).exists():
            (dest / "profile").mkdir(exist_ok=True)
            shutil.copy2(src / "profile" / name, dest / "profile" / name)
            n += 1
    for sub in ("photos", "raw"):
        for f in sorted((src / sub).rglob("*")):
            if f.is_file() and not f.is_symlink() and f.stat().st_size <= MAX_STAGED_FILE_MB * 1024 * 1024:
                out = dest / f.relative_to(src)
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, out)
                n += 1
    return n


def claude_run(job, ws, prompt, resume=None):
    stream = claude_cli.Stream(job, ws)

    def on_line(line):
        stream.feed(line)
        if stream.abort and job.proc:
            kill_tree(job.proc)

    code = job.run_cmd(claude_cli.argv(resume), cwd=ws, env=claude_cli.child_env(), stdin_text=prompt,
                       timeout=config.CLAUDE_TIMEOUT_S, idle_timeout=config.CLAUDE_IDLE_S, on_line=on_line)
    why = stream.failure(code)
    if why:
        raise JobError(why)
    res = stream.result or {}
    job.log(f"Analysis finished in {round((res.get('duration_ms') or 0) / 1000)}s "
            f"({res.get('num_turns', '?')} turns, {stream.web_calls} web calls).")
    return stream.session_id


def check_design(out):
    """Problems with the design system Claude wrote; empty when it is usable."""
    return check_outputs(out, ("design_system",), required="design_system")


def check_outputs(out, names=OUTPUTS, required="profile"):
    """Problems with the files Claude wrote; empty when they are usable."""
    bad = []
    if not (out / f"{required}.json").exists():
        return [f"out/{required}.json was not written"]
    for n in names:
        f = out / f"{n}.json"
        if not f.exists():
            continue
        if f.is_symlink() or not f.is_file():
            bad.append(f"out/{n}.json is not a regular file")
            continue
        if f.stat().st_size > MAX_OUTPUT_KB * 1024:
            bad.append(f"out/{n}.json is larger than {MAX_OUTPUT_KB} KB")
            continue
        data, problems = ingest.check_file(f, n)
        bad += problems
        if n == "profile" and isinstance(data, dict) and isinstance(data.get("pitch_hooks"), list) \
                and len(data["pitch_hooks"]) != 3:
            bad.append(f"profile.pitch_hooks should have exactly 3 items, has {len(data['pitch_hooks'])}")
    return bad
