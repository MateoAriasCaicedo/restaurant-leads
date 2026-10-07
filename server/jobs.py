"""Background jobs: pipeline stages run as subprocesses, with their output kept as a pollable log.

Two lanes:
  pipeline  discover / audit / re-render; a serial queue (Overpass is a shared service: one area at a time)
  enrich    the headless-Claude analysis; one at a time and never queued, so a lead is only ever
            analyzed by an explicit click

Stages run as child processes rather than in-process because they report progress with print(), exit with
sys.exit(), and audit.py keeps a module-level PageSpeed circuit breaker that must not outlive a run.
"""
import atexit
import json
import os
import queue
import secrets
import subprocess
import sys
import threading
import time
from pathlib import Path

from leadgen import config

from . import ROOT

ACTIVE = ("queued", "running")
MAX_LINES = 5000
KEEP_IN_MEMORY = 50
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class JobError(Exception):
    """A step failed; the message is shown to the user."""


class Cancelled(Exception):
    pass


class Job:
    def __init__(self, kind, title, lane, params=None, lead=None, steps=()):
        self.id = time.strftime("%Y%m%d-%H%M%S-") + secrets.token_hex(2)
        self.kind, self.title, self.lane = kind, title, lane
        self.params = params or {}
        self.lead = lead                  # {"key", "name"} when the job is about one lead
        self.status = "queued"
        self.steps = [{"name": n, "label": label, "status": "pending"} for n, label in steps]
        self.step = None
        self.error = None
        self.result = {}
        self.created = time.time()
        self.started = self.ended = None
        self.lines, self.seq = [], 0
        self.cancel_requested = False
        self.proc = None
        self.lock = threading.Lock()

    @property
    def dir(self):
        return ROOT / config.RUNS_DIR / self.id

    def public(self):
        return {"id": self.id, "kind": self.kind, "title": self.title, "lane": self.lane, "params": self.params,
                "lead": self.lead, "status": self.status, "steps": self.steps, "step": self.step,
                "error": self.error, "result": self.result, "created": self.created,
                "started": self.started, "ended": self.ended, "line_count": self.seq}

    def save(self):
        try:
            self.dir.mkdir(parents=True, exist_ok=True)
            (self.dir / "job.json").write_text(json.dumps(self.public(), ensure_ascii=False, indent=1), "utf-8")
        except OSError:
            pass

    # --- called from the worker thread ---

    def log(self, text, level="info"):
        with self.lock:
            self.seq += 1
            line = {"seq": self.seq, "t": time.time(), "step": self.step, "level": level, "text": text.rstrip()}
            self.lines.append(line)
            if len(self.lines) > MAX_LINES:
                del self.lines[: len(self.lines) - MAX_LINES]
        try:
            self.dir.mkdir(parents=True, exist_ok=True)
            with open(self.dir / "log.txt", "a", encoding="utf-8") as f:
                f.write(f"[{self.step or '-'}] {line['text']}\n")
        except OSError:
            pass

    def begin(self, name):
        """Start a named step (finishing the previous one)."""
        self.check_cancel()
        self._close_step("done")
        self.step = name
        for s in self.steps:
            if s["name"] == name:
                s["status"], s["started"] = "running", time.time()
        self.save()

    def _close_step(self, status):
        for s in self.steps:
            if s["status"] == "running":
                s["status"], s["ended"] = status, time.time()

    def check_cancel(self):
        if self.cancel_requested:
            raise Cancelled()

    def run_cmd(self, argv, cwd=None, env=None, stdin_text=None, timeout=None, idle_timeout=None, on_line=None):
        """Run a child process, streaming its output into the log (or to on_line). Returns the exit code.
        Raises Cancelled / JobError on cancel, timeout or stall."""
        self.check_cancel()
        proc = subprocess.Popen(
            argv, cwd=str(cwd or ROOT), env=env or python_env(), stdin=subprocess.PIPE if stdin_text is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
            bufsize=1, creationflags=NO_WINDOW)
        self.proc = proc
        state = {"last": time.time(), "why": None}
        t0 = time.time()

        def watch():
            while proc.poll() is None:
                now = time.time()
                if self.cancel_requested:
                    state["why"] = "cancelled"
                elif timeout and now - t0 > timeout:
                    state["why"] = f"timed out after {int(timeout)}s"
                elif idle_timeout and now - state["last"] > idle_timeout:
                    state["why"] = f"no output for {int(idle_timeout)}s"
                if state["why"]:
                    kill_tree(proc)
                    return
                time.sleep(0.5)

        threading.Thread(target=watch, daemon=True).start()
        if stdin_text is not None:
            try:
                proc.stdin.write(stdin_text)
                proc.stdin.close()
            except OSError:
                pass
        for line in proc.stdout:
            state["last"] = time.time()
            if on_line:
                on_line(line.rstrip("\n"))
            elif line.strip():
                self.log(line)
        code = proc.wait()
        self.proc = None
        if self.cancel_requested:
            raise Cancelled()
        if state["why"]:
            raise JobError(f"Stopped: {state['why']}")
        return code


def python_env():
    env = dict(os.environ)
    env.update(PYTHONUTF8="1", PYTHONUNBUFFERED="1")
    return env


def python(*args):
    """argv for a pipeline script, on the same interpreter as the server (never the bare `python` alias)."""
    return [sys.executable, "-u", *args]


def kill_tree(proc):
    if proc.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True, creationflags=NO_WINDOW)
    else:
        proc.kill()


class Manager:
    def __init__(self):
        self.jobs = {}                    # id -> Job (recent) or dict (loaded from disk)
        self.order = []
        self.lock = threading.Lock()
        self.pipeline = queue.Queue()
        self.worker = None
        atexit.register(self.shutdown)

    # --- history ---

    def load_history(self):
        """Read finished jobs from .runs/. Anything still marked active belonged to a server that stopped."""
        runs = ROOT / config.RUNS_DIR
        if not runs.exists():
            return
        found = sorted((d for d in runs.iterdir() if (d / "job.json").exists()), key=lambda d: d.name)
        for d in found[-KEEP_IN_MEMORY:]:
            try:
                data = json.loads((d / "job.json").read_text("utf-8"))
            except (OSError, ValueError):
                continue
            if data.get("status") in ACTIVE:
                data["status"], data["error"] = "interrupted", "The server stopped while this job was running."
                for s in data.get("steps", []):
                    if s["status"] == "running":
                        s["status"] = "failed"
                (d / "job.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), "utf-8")
            self.jobs[data["id"]] = data
            self.order.append(data["id"])

    def public(self, j):
        return j.public() if isinstance(j, Job) else j

    def list(self):
        with self.lock:
            return [self.public(self.jobs[i]) for i in reversed(self.order)]

    def get(self, job_id, after=0):
        j = self.jobs.get(job_id)
        if j is None:
            return None
        if isinstance(j, Job):
            with j.lock:
                lines = [ln for ln in j.lines if ln["seq"] > after]
            return {"job": j.public(), "lines": lines, "next": j.seq}
        lines = []
        log = ROOT / config.RUNS_DIR / job_id / "log.txt"
        if after == 0 and log.exists():
            for i, raw in enumerate(log.read_text("utf-8", errors="replace").splitlines()[-MAX_LINES:], 1):
                step, _, text = raw.partition("] ")
                lines.append({"seq": i, "t": None, "step": step.lstrip("[") or None, "level": "info", "text": text})
        return {"job": j, "lines": lines, "next": max(after, len(lines))}

    def active(self, lane=None, kind=None, lead_key=None):
        with self.lock:
            for i in reversed(self.order):
                j = self.jobs[i]
                if (isinstance(j, Job) and j.status in ACTIVE and (lane is None or j.lane == lane)
                        and (kind is None or j.kind == kind)
                        and (lead_key is None or (j.lead or {}).get("key") == lead_key)):
                    return j
        return None

    # --- submitting ---

    def _add(self, job):
        with self.lock:
            self.jobs[job.id] = job
            self.order.append(job.id)
            for old in self.order[:-KEEP_IN_MEMORY]:
                if not (isinstance(self.jobs[old], Job) and self.jobs[old].status in ACTIVE):
                    self.jobs.pop(old)
                    self.order.remove(old)
        job.save()

    def submit(self, job, fn):
        """Queue a pipeline job. An identical job that is already waiting or running is returned instead."""
        with self.lock:
            for i in self.order:
                j = self.jobs[i]
                if isinstance(j, Job) and j.status in ACTIVE and j.kind == job.kind and j.params == job.params:
                    return j
        self._add(job)
        self.pipeline.put((job, fn))
        if not (self.worker and self.worker.is_alive()):
            self.worker = threading.Thread(target=self._drain, daemon=True)
            self.worker.start()
        return job

    def start_exclusive(self, job, fn):
        """Start a job on its own thread, or return None if its lane is busy."""
        if self.active(lane=job.lane):
            return None
        self._add(job)
        threading.Thread(target=self._run, args=(job, fn), daemon=True).start()
        return job

    def _drain(self):
        while True:
            job, fn = self.pipeline.get()
            self._run(job, fn)

    def _run(self, job, fn):
        if job.cancel_requested:
            job.status, job.ended = "cancelled", time.time()
            job.save()
            return
        job.status, job.started = "running", time.time()
        job.save()
        try:
            fn(job)
            job._close_step("done")
            job.status = "succeeded"
        except Cancelled:
            job._close_step("cancelled")
            job.status = "cancelled"
            job.log("Cancelled.", "warn")
        except JobError as e:
            job._close_step("failed")
            job.status, job.error = "failed", str(e)
            job.log(str(e), "error")
        except Exception as e:                       # a bug in a job must not take the worker down
            job._close_step("failed")
            job.status, job.error = "failed", f"{type(e).__name__}: {e}"
            job.log(job.error, "error")
        job.step, job.ended = None, time.time()
        job.save()

    def cancel(self, job_id):
        j = self.jobs.get(job_id)
        if not isinstance(j, Job) or j.status not in ACTIVE:
            return False
        j.cancel_requested = True
        if j.proc:
            kill_tree(j.proc)
        return True

    def shutdown(self):
        for j in list(self.jobs.values()):
            if isinstance(j, Job) and j.proc:
                kill_tree(j.proc)


manager = Manager()


# --- simple pipeline jobs ---

def _script_job(kind, title, argv, params, lead=None, failure="The stage exited with an error; see the log."):
    job = Job(kind, title, "pipeline", params, lead, steps=[(kind, title)])

    def run(job):
        job.begin(kind)
        if job.run_cmd(argv) != 0:
            raise JobError(failure)

    return manager.submit(job, run)


def discover(area):
    return _script_job("discover", f"Discover {area}", python("discover.py", area), {"area": area},
                       failure="OpenStreetMap returned no data for this area (all mirrors failed, or the area is empty).")


def audit(refresh=False):
    argv = python("audit.py") + (["--refresh"] if refresh else [])
    return _script_job("audit", "Re-audit every place" if refresh else "Audit new and broken sites", argv, {"refresh": refresh})


# Maintenance tasks on the pipeline lane: task -> (title, script and flags, failure text)
MAINTENANCE = {
    "find_sites": ("Look for websites of places listed without one", ("audit.py", "--discover"),
                   "The website search exited with an error; see the log."),
    "pagespeed": ("Fill missing PageSpeed scores", ("audit.py", "--perf"),
                  "The speed check exited with an error; see the log."),
    "rescore": ("Recompute website scores from stored audits", ("audit.py", "--rescore"),
                "Recomputing the scores failed; see the log."),
    "backfill": ("Import saved Google Maps data", ("quality.py", "--backfill"),
                 "Importing the saved Maps data failed; see the log."),
}


def maintenance(task):
    title, argv, failure = MAINTENANCE[task]
    return _script_job(task, title, python(*argv), {"task": task}, failure=failure)


def quality_scrape(n, area=None):
    argv = python("quality.py", "--scrape", str(n)) + (["--area", area] if area else [])
    where = f" in {area}" if area else ""
    return _script_job("quality", f"Verify {n} premium candidates on Maps{where}", argv, {"n": n, "area": area},
                       failure="The Maps check exited with an error; see the log (is Playwright installed?).")


def scrape_one(place_id, lead, sources):
    argv = python("scrape.py", place_id) + (["--only", sources[0]] if len(sources) == 1 else [])
    return _script_job("scrape", f"Read public pages: {lead['name']}", argv, {"place_id": place_id, "sources": list(sources)}, lead,
                       failure="Reading the public pages failed; see the log.")


def audit_one(place_id, lead):
    return _script_job("audit_one", f"Re-check website: {lead['name']}", python("audit.py", "--only", place_id),
                       {"place_id": place_id}, lead)

