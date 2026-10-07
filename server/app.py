"""HTTP routes. Everything under /api is JSON; anything else serves the built UI (ui/dist)."""
import io
import json
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path

from leadgen import config
from leadgen.scoring import score
from leadgen.enrichment import scrape
from leadgen import store
from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.background import BackgroundTask
from starlette.middleware import Middleware
from starlette.responses import FileResponse, JSONResponse, PlainTextResponse, Response, StreamingResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from . import ROOT, buildplan, designsystem, enrich_job, files, jobs, leads, outreach
from .leads import db
from .security import Guard

DIST = ROOT / "ui" / "dist"
FILE_CSP = "sandbox; default-src 'none'"


class ApiError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message


def ok(data=None, status=200):
    return JSONResponse(data if data is not None else {"ok": True}, status)


async def body(request):
    try:
        data = await request.json()
    except (ValueError, UnicodeDecodeError):
        raise ApiError(400, "Expected a JSON body") from None
    if not isinstance(data, dict):
        raise ApiError(400, "Expected a JSON object")
    return data


def lead_ref(p):
    return {"key": store.key(p["place_id"]), "name": p["name"]}


# --- reads ---

async def get_meta(request):
    with db() as con:
        return ok(leads.meta(con))


def _list(include_excluded):
    with db() as con:
        return leads.list_leads(con, include_excluded)


async def get_leads(request):
    return ok(await run_in_threadpool(_list, request.query_params.get("include_excluded") == "1"))


def _detail(key):
    with db() as con:
        return leads.lead_detail(con, key)


async def get_lead(request):
    return ok(await run_in_threadpool(_detail, request.path_params["key"]))


async def get_build_plan(request):
    detail = await run_in_threadpool(_detail, request.path_params["key"])
    md = buildplan.render(detail)
    if md is None:
        raise leads.NotFound("This lead has no build plan yet. Research it first.")
    return Response(md, media_type="text/markdown; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{detail["slug"]}-build-plan.md"'})


async def get_design_system(request):
    detail = await run_in_threadpool(_detail, request.path_params["key"])
    md = designsystem.render(detail)
    if md is None:
        raise leads.NotFound("This lead has no design system yet. Research it again.")
    return Response(md, media_type="text/markdown; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{detail["slug"]}-design-system.md"'})


async def export_csv(request):
    with db() as con:
        rows, _, _ = score.ranked(con)
    buf = io.StringIO(newline="")
    score.write_csv(rows, buf)
    return Response("﻿" + buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="leads_ranked.csv"'})


# --- lead writes ---

async def put_status(request):
    data = await body(request)
    status = data.get("status")
    if status is not None and status not in store.STATUSES:
        raise ApiError(400, f"status must be null or one of: {', '.join(store.STATUSES)}")
    with db() as con:
        p = leads.place_or_404(con, request.path_params["key"])
        if status is None:
            store.clear_status(con, p["place_id"])
        else:
            store.set_status(con, p["place_id"], status)
            if status == "approved":
                store.lead_dir(p)                    # same as approve.py: make the photo folders
    return ok({"status": status})


async def put_notes_file(request):
    data = await body(request)
    with db() as con:
        p = leads.place_or_404(con, request.path_params["key"])
        files.write_notes(store.lead_dir(p), data.get("text") or "")
    return ok()


async def put_private_note(request):
    data = await body(request)
    with db() as con:
        p = leads.place_or_404(con, request.path_params["key"])
        return ok(outreach.set_note(con, p["place_id"], data.get("body") or ""))


async def post_contact(request):
    data = await body(request)
    with db() as con:
        p = leads.place_or_404(con, request.path_params["key"])
        status = outreach.add_contact(con, p["place_id"], data)
        return ok({"status": status, "contacts": outreach.contacts(con, p["place_id"])}, 201)


async def patch_contact(request):
    data = await body(request)
    with db() as con:
        row = outreach.update_contact(con, request.path_params["id"], data)
        if row is None:
            raise leads.NotFound("No such contact")
        return ok(dict(row))


async def delete_contact(request):
    with db() as con:
        if outreach.delete_contact(con, request.path_params["id"]) is None:
            raise leads.NotFound("No such contact")
    return ok()


# --- files ---

def _lead_dir(key, create=False):
    with db() as con:
        return store.lead_dir(leads.place_or_404(con, key), create=create)


async def get_file(request):
    pp = request.path_params
    f = files.resolve(_lead_dir(pp["key"]), pp["kind"], pp["name"])
    if not f.is_file():
        raise leads.NotFound("No such file")
    headers = {"Content-Security-Policy": FILE_CSP, "Cache-Control": "private, max-age=300"}
    if request.query_params.get("download"):
        return FileResponse(f, media_type=files.MEDIA[f.suffix.lower()], headers=headers, filename=f.name,
                            content_disposition_type="attachment")
    w = request.query_params.get("w")
    if w:
        if not w.isdigit():
            raise files.Invalid("Bad thumbnail request")
        try:
            data = await run_in_threadpool(files.thumbnail, f, int(w))
        except files.Invalid:
            raise
        except Exception:
            raise leads.NotFound("This image could not be read") from None
        return Response(data, media_type="image/jpeg", headers=headers)
    if f.suffix.lower() == ".pdf":
        headers["Content-Disposition"] = "attachment"
    return FileResponse(f, media_type=files.MEDIA[f.suffix.lower()], headers=headers)


async def get_files_zip(request):
    """Every file of one group (?kind=maps) or of all groups, as one zip, one folder per group."""
    kind = request.query_params.get("kind")
    d = _lead_dir(request.path_params["key"])
    tmp, count, size = await run_in_threadpool(files.archive, d, [kind] if kind else list(files.KINDS))
    if not count:
        tmp.close()
        raise leads.NotFound("Nothing to download")
    headers = {"Content-Length": str(size), "Cache-Control": "no-store",
               "Content-Disposition": f'attachment; filename="{d.name}-{kind or "materials"}.zip"'}
    return StreamingResponse(iter(lambda: tmp.read(1 << 16), b""), media_type="application/zip", headers=headers,
                             background=BackgroundTask(tmp.close))


async def post_files(request):
    pp = request.path_params
    if jobs.manager.active(kind="enrich", lead_key=pp["key"]):
        raise ApiError(409, "An analysis of this lead is running; add files when it finishes.")
    d = _lead_dir(pp["key"], create=True)
    saved, errors = [], []
    async with request.form(max_files=20, max_part_size=config.MAX_UPLOAD_MB * 1024 * 1024 + 1024) as form:
        for item in form.getlist("files"):
            if not hasattr(item, "read"):
                continue
            data = await item.read()
            try:
                saved.append(files.save_upload(d, pp["kind"], item.filename, data))
            except files.Invalid as e:
                errors.append(str(e))
    if not saved and not errors:
        raise ApiError(400, "No files in the request")
    return ok({"saved": saved, "errors": errors, "files": files.listing(d, pp["kind"], pp["key"])},
              201 if saved else 400)


async def delete_file(request):
    pp = request.path_params
    if jobs.manager.active(kind="enrich", lead_key=pp["key"]):
        raise ApiError(409, "An analysis of this lead is running; remove files when it finishes.")
    d = _lead_dir(pp["key"])
    files.trash(d, pp["kind"], pp["name"])
    return ok({"files": files.listing(d, pp["kind"], pp["key"])})


async def get_context(request):
    f = _lead_dir(request.path_params["key"]) / "context.md"
    if not f.is_file():
        raise leads.NotFound("Nothing has been collected for this lead yet")
    return FileResponse(f, media_type="text/plain; charset=utf-8")


# --- jobs ---

async def post_enrich(request):
    data = await body(request)
    with db() as con:
        p = leads.place_or_404(con, request.path_params["key"])
    job = enrich_job.start(p, dry_run=bool(data.get("dry_run")), scrape=bool(data.get("scrape")))
    if job is None:
        busy = jobs.manager.active(lane="enrich")
        raise ApiError(409, f"Another analysis is running ({busy.lead['name'] if busy and busy.lead else 'unknown'}). "
                            "Leads are analyzed one at a time.")
    return ok({"job": job.public()}, 202)


async def post_design_system(request):
    """Write only the design system of a lead that is already researched (no new web research)."""
    await body(request)
    with db() as con:
        p = leads.place_or_404(con, request.path_params["key"])
    if not (store.lead_dir(p, create=False) / "profile" / "profile.json").is_file():
        raise ApiError(400, "Research this lead first: the design system is written from its profile.")
    job = enrich_job.start_design(p)
    if job is None:
        busy = jobs.manager.active(lane="enrich")
        raise ApiError(409, f"Another analysis is running ({busy.lead['name'] if busy and busy.lead else 'unknown'}). "
                            "Leads are analyzed one at a time.")
    return ok({"job": job.public()}, 202)


async def post_lead_scrape(request):
    data = await body(request)
    sources = [s for s in dict.fromkeys(data.get("sources") or scrape.SOURCES) if s in scrape.SOURCES]
    if not sources:
        raise ApiError(400, "sources must be maps and/or instagram")
    if not scrape.installed():
        raise ApiError(400, "Playwright is not installed: pip install playwright && python -m playwright install chromium")
    with db() as con:
        p = leads.place_or_404(con, request.path_params["key"])
    if jobs.manager.active(lead_key=store.key(p["place_id"])):
        raise ApiError(409, "Another job is running for this lead.")
    return ok({"job": jobs.scrape_one(p["place_id"], lead_ref(p), sources).public()}, 202)


async def post_lead_audit(request):
    with db() as con:
        p = leads.place_or_404(con, request.path_params["key"])
    return ok({"job": jobs.audit_one(p["place_id"], lead_ref(p)).public()}, 202)


async def post_discover(request):
    area = (await body(request)).get("area")
    if area not in config.ALL_AREAS:
        raise ApiError(400, f"Unknown area. Known areas: {', '.join(config.ALL_AREAS)}")
    return ok({"job": jobs.discover(area).public()}, 202)


async def post_quality(request):
    data = await body(request)
    n, area = data.get("n"), data.get("area") or None
    if not isinstance(n, int) or isinstance(n, bool) or not 1 <= n <= 25:
        raise ApiError(400, "n must be a whole number from 1 to 25.")
    if area is not None and area not in config.ALL_AREAS:
        raise ApiError(400, f"Unknown area. Known areas: {', '.join(config.ALL_AREAS)}")
    if not scrape.installed():
        raise ApiError(409, "Playwright is not installed: pip install playwright && python -m playwright install chromium")
    return ok({"job": jobs.quality_scrape(n, area).public()}, 202)


async def post_maintenance(request):
    task = (await body(request)).get("task")
    if task not in jobs.MAINTENANCE:
        raise ApiError(400, f"task must be one of: {', '.join(jobs.MAINTENANCE)}")
    return ok({"job": jobs.maintenance(task).public()}, 202)


async def post_audit(request):
    return ok({"job": jobs.audit(bool((await body(request)).get("refresh"))).public()}, 202)


async def get_jobs(request):
    return ok({"jobs": jobs.manager.list()})


async def get_job(request):
    after = request.query_params.get("after", "0")
    out = jobs.manager.get(request.path_params["id"], int(after) if after.isdigit() else 0)
    if out is None:
        raise leads.NotFound("No such job")
    return ok(out)


async def cancel_job(request):
    if not jobs.manager.cancel(request.path_params["id"]):
        raise ApiError(409, "This job is not running.")
    return ok()


# --- UI ---

async def spa(request):
    if not (DIST / "index.html").is_file():
        return PlainTextResponse("The UI is not built yet. Run:  npm --prefix ui install  &&  npm --prefix ui run build\n"
                                 "(or use the dev server:  npm --prefix ui run dev)", 503)
    f = (DIST / request.path_params.get("path", "")).resolve()
    if f.is_file() and f.is_relative_to(DIST.resolve()):
        return FileResponse(f)
    return FileResponse(DIST / "index.html", headers={"Cache-Control": "no-cache"})


async def api_404(request):
    return JSONResponse({"error": "No such endpoint"}, 404)


def _error(status):
    async def handler(request, exc):
        return JSONResponse({"error": str(exc)}, status)
    return handler


async def api_error(request, exc):
    return JSONResponse({"error": exc.message}, exc.status)


async def db_error(request, exc):
    busy = "locked" in str(exc)
    return JSONResponse({"error": "The database is busy (a pipeline job is writing). Try again in a moment." if busy
                         else f"Database error: {exc}"}, 503 if busy else 500)


@asynccontextmanager
async def lifespan(app):
    leads.ensure_schema()
    jobs.manager.load_history()
    yield
    jobs.manager.shutdown()


L = "/api/leads/{key}"
routes = [
    Route("/api/meta", get_meta),
    Route("/api/leads", get_leads),
    Route("/api/export/leads.csv", export_csv),
    Route(L, get_lead),
    Route(L + "/status", put_status, methods=["PUT"]),
    Route(L + "/notes-file", put_notes_file, methods=["PUT"]),
    Route(L + "/private-note", put_private_note, methods=["PUT"]),
    Route(L + "/contacts", post_contact, methods=["POST"]),
    Route("/api/contacts/{id:int}", patch_contact, methods=["PATCH"]),
    Route("/api/contacts/{id:int}", delete_contact, methods=["DELETE"]),
    Route(L + "/files.zip", get_files_zip),
    Route(L + "/files/{kind}", post_files, methods=["POST"]),
    Route(L + "/files/{kind}/{name}", get_file),
    Route(L + "/files/{kind}/{name}", delete_file, methods=["DELETE"]),
    Route(L + "/context.md", get_context),
    Route(L + "/build-plan.md", get_build_plan),
    Route(L + "/design-system.md", get_design_system),
    Route(L + "/enrich", post_enrich, methods=["POST"]),
    Route(L + "/design-system", post_design_system, methods=["POST"]),
    Route(L + "/audit", post_lead_audit, methods=["POST"]),
    Route(L + "/scrape", post_lead_scrape, methods=["POST"]),
    Route("/api/jobs/discover", post_discover, methods=["POST"]),
    Route("/api/jobs/audit", post_audit, methods=["POST"]),
    Route("/api/jobs/quality", post_quality, methods=["POST"]),
    Route("/api/jobs/maintenance", post_maintenance, methods=["POST"]),
    Route("/api/jobs", get_jobs),
    Route("/api/jobs/{id}", get_job),
    Route("/api/jobs/{id}/cancel", cancel_job, methods=["POST"]),
    Route("/api/{rest:path}", api_404, methods=["GET", "POST", "PUT", "PATCH", "DELETE"]),
]
if (DIST / "assets").is_dir():
    routes.append(Mount("/assets", StaticFiles(directory=DIST / "assets")))
routes.append(Route("/{path:path}", spa))

app = Starlette(
    routes=routes, lifespan=lifespan, middleware=[Middleware(Guard)],
    exception_handlers={
        ApiError: api_error, leads.NotFound: _error(404), files.Invalid: _error(400), outreach.Invalid: _error(400),
        sqlite3.OperationalError: db_error, json.JSONDecodeError: _error(400),
    },
)
