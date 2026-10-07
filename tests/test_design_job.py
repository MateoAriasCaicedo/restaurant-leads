"""Writing only the design system of an already researched lead: the job stages the finished profile, asks Claude for
out/design_system.json alone, validates it (one repair round) and saves it next to the profile."""
import copy
import json
import shutil
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

from starlette.testclient import TestClient

from leadgen import config, store
from server import app as server_app
from server import claude_cli, enrich_job, jobs
from tests.design_fixture import DS

HEADERS = {"X-Leads-UI": "1", "Origin": "http://127.0.0.1:8642"}
PLACE = {"place_id": "osm:node/1", "name": "La Parrilla"}
PROFILE = {"identity": {"cuisine": ["Colombian"], "price_tier": "mid", "positioning": "Family grill"}}


class DesignJob(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        for target, name, value in ((jobs, "ROOT", self.tmp), (enrich_job, "ROOT", self.tmp), (config, "RUNS_DIR", "runs"),
                                    (config, "LEADS_DIR", str(self.tmp / "leads"))):
            p = mock.patch.object(target, name, value)
            p.start()
            self.addCleanup(p.stop)
        p = mock.patch.object(claude_cli, "binary", return_value="claude")
        p.start()
        self.addCleanup(p.stop)

        self.lead = store.lead_dir(PLACE)
        self.profile_json = json.dumps(PROFILE)
        (self.lead / "profile" / "profile.json").write_text(self.profile_json, "utf-8")
        (self.lead / "profile" / "menu.json").write_text('{"sections": []}', "utf-8")
        (self.lead / "context.md").write_text("# Collected\nPalette: #2b2a29\n\n## To finish this lead\nignore this", "utf-8")
        (self.lead / "schemas.json").write_text('{"profile": {}}', "utf-8")       # written before design systems existed
        (self.lead / "photos" / "maps" / "a.jpg").write_bytes(b"jpg")
        self.target = self.lead / "profile" / "design_system.json"
        self.job = jobs.Job("enrich", "Design system", "enrich", {"mode": "design"}, {"key": "osm-node-1", "name": "La Parrilla"}, enrich_job.DESIGN_STEPS)
        self.job.run_cmd = mock.Mock(side_effect=AssertionError("the design job must not run any script (no collect, no ingest)"))

    def fake_claude(self, *outputs):
        """claude_run that writes the next output each time it is called, and records what it was given."""
        calls = []

        def run(job, ws, prompt, resume=None):
            calls.append({"prompt": prompt, "resume": resume, "files": sorted(p.relative_to(ws).as_posix() for p in ws.rglob("*") if p.is_file()),
                          "schemas": json.loads((ws / "leads" / self.lead.name / "schemas.json").read_text("utf-8")),
                          "context": (ws / "leads" / self.lead.name / "context.md").read_text("utf-8")})
            (ws / "out" / "design_system.json").write_text(json.dumps(outputs[min(len(calls), len(outputs)) - 1]), "utf-8")
            return "session-1"

        p = mock.patch.object(enrich_job, "claude_run", run)
        p.start()
        self.addCleanup(p.stop)
        return calls

    def bad(self):
        return DS | {"colors": [{"name": "x", "hex": "red", "role": "ink"}]}

    def test_saves_the_design_system_and_touches_nothing_else(self):
        calls = self.fake_claude(DS)
        enrich_job.run_design(self.job, PLACE)
        self.assertEqual(json.loads(self.target.read_text("utf-8")), DS)
        self.assertEqual((self.lead / "profile" / "profile.json").read_text("utf-8"), self.profile_json)
        self.assertEqual((self.lead / "schemas.json").read_text("utf-8"), '{"profile": {}}')    # the lead's own folder is not rewritten
        self.assertEqual(self.job.result, {"files": ["design_system"]})
        self.assertFalse((self.job.dir / "ws").exists(), "the workspace was only a copy")
        self.assertEqual(len(calls), 1)

    def test_the_workspace_has_the_finished_analysis_and_only_the_design_schema(self):
        calls = self.fake_claude(DS)
        enrich_job.run_design(self.job, PLACE)
        files = calls[0]["files"]
        for want in (f"leads/{self.lead.name}/profile/profile.json", f"leads/{self.lead.name}/profile/menu.json", f"leads/{self.lead.name}/context.md",
                     f"leads/{self.lead.name}/photos/maps/a.jpg", f"leads/{self.lead.name}/schemas.json"):
            self.assertIn(want, files)
        self.assertEqual(list(calls[0]["schemas"]), ["design_system"])
        self.assertNotIn("ignore this", calls[0]["context"])                    # the CLI workflow's closing notes stay out

    def test_the_prompt_asks_for_the_design_system_only(self):
        calls = self.fake_claude(DS)
        enrich_job.run_design(self.job, PLACE)
        prompt = calls[0]["prompt"]
        self.assertIn(f"leads/{self.lead.name}/", prompt)
        self.assertIn("La Parrilla", prompt)
        self.assertIn("Next.js and Tailwind CSS", prompt)
        self.assertIn("Do not search or fetch anything", prompt)
        self.assertIn("out/design_system.json", prompt)
        self.assertIn("`next/font/google`", prompt)                             # the shared design rules were filled in
        self.assertNotRegex(prompt, r"\{[a-z_]+\}")

    def test_the_previous_design_system_is_kept(self):
        self.target.write_text('{"concept": "old"}', "utf-8")
        self.fake_claude(DS)
        enrich_job.run_design(self.job, PLACE)
        self.assertEqual(json.loads((self.job.dir / "prev" / "design_system.json").read_text("utf-8")), {"concept": "old"})
        self.assertEqual(json.loads(self.target.read_text("utf-8")), DS)

    def test_one_repair_round_is_allowed(self):
        calls = self.fake_claude(self.bad(), DS)
        enrich_job.run_design(self.job, PLACE)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[1]["resume"], "session-1")
        self.assertIn("design_system.colors[0].hex", calls[1]["prompt"])
        self.assertEqual(json.loads(self.target.read_text("utf-8")), DS)

    def test_a_system_that_stays_invalid_is_not_saved(self):
        self.target.write_text('{"concept": "old"}', "utf-8")
        calls = self.fake_claude(self.bad())
        with self.assertRaises(jobs.JobError) as ctx:
            enrich_job.run_design(self.job, PLACE)
        self.assertIn("did not pass validation", str(ctx.exception))
        self.assertEqual(len(calls), 2)
        self.assertEqual(json.loads(self.target.read_text("utf-8")), {"concept": "old"})

    def test_a_missing_output_file_is_a_problem(self):
        def silent(job, ws, prompt, resume=None):
            return "session-1"
        with mock.patch.object(enrich_job, "claude_run", silent):
            with self.assertRaises(jobs.JobError) as ctx:
                enrich_job.run_design(self.job, PLACE)
        self.assertIn("out/design_system.json was not written", str(ctx.exception))
        self.assertFalse(self.target.exists())

    def test_an_unresearched_lead_is_refused_before_claude_runs(self):
        (self.lead / "profile" / "profile.json").unlink()
        calls = self.fake_claude(DS)
        with self.assertRaises(jobs.JobError) as ctx:
            enrich_job.run_design(self.job, PLACE)
        self.assertIn("not been researched", str(ctx.exception))
        self.assertEqual(calls, [])

    def test_needs_the_claude_cli(self):
        calls = self.fake_claude(DS)
        with mock.patch.object(claude_cli, "binary", return_value=None):
            with self.assertRaises(jobs.JobError):
                enrich_job.run_design(self.job, PLACE)
        self.assertEqual(calls, [])

    def test_the_regular_check_still_requires_a_profile(self):
        out = self.tmp / "out"
        out.mkdir()
        (out / "design_system.json").write_text(json.dumps(DS), "utf-8")
        self.assertEqual(enrich_job.check_outputs(out), ["out/profile.json was not written"])
        self.assertEqual(enrich_job.check_design(out), [])


class StartDesign(unittest.TestCase):
    def test_runs_in_the_enrich_lane_so_it_never_overlaps_a_research_run(self):
        started = []
        with mock.patch.object(enrich_job.manager, "start_exclusive", side_effect=lambda job, fn: started.append(job) or job):
            job = enrich_job.start_design(PLACE)
        self.assertIs(job, started[0])
        self.assertEqual((job.kind, job.lane), ("enrich", "enrich"))
        self.assertEqual(job.params, {"place_id": "osm:node/1", "mode": "design"})
        self.assertEqual(job.lead, {"key": "osm-node-1", "name": "La Parrilla"})
        self.assertEqual([s["name"] for s in job.steps], ["prepare", "stage", "analyze", "validate", "promote"])

    def test_returns_none_while_another_analysis_runs(self):
        with mock.patch.object(enrich_job.manager, "start_exclusive", return_value=None):
            self.assertIsNone(enrich_job.start_design(PLACE))


class Route(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(server_app.app, base_url="http://127.0.0.1:8642")
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)

        @contextmanager
        def no_db():
            yield None

        for target, name, value in ((server_app, "db", no_db), (server_app.leads, "place_or_404", lambda con, key: dict(PLACE)),
                                    (server_app.store, "lead_dir", lambda p, create=True: self.tmp)):
            p = mock.patch.object(target, name, value)
            p.start()
            self.addCleanup(p.stop)

    def post(self, headers=HEADERS):
        return self.client.post("/api/leads/osm-node-1/design-system", json={}, headers=headers)

    def researched(self):
        (self.tmp / "profile").mkdir()
        (self.tmp / "profile" / "profile.json").write_text("{}", "utf-8")

    def test_starts_the_job(self):
        self.researched()
        job = jobs.Job("enrich", "Design system: La Parrilla", "enrich", {"mode": "design"}, {"key": "osm-node-1", "name": "La Parrilla"}, enrich_job.DESIGN_STEPS)
        with mock.patch.object(enrich_job, "start_design", return_value=job) as start:
            r = self.post()
        self.assertEqual(r.status_code, 202)
        self.assertEqual(r.json()["job"]["params"]["mode"], "design")
        start.assert_called_once()

    def test_refuses_a_lead_that_has_not_been_researched(self):
        with mock.patch.object(enrich_job, "start_design") as start:
            r = self.post()
        self.assertEqual(r.status_code, 400)
        self.assertIn("Research this lead first", r.json()["error"])
        start.assert_not_called()

    def test_says_so_when_another_analysis_is_running(self):
        self.researched()
        with mock.patch.object(enrich_job, "start_design", return_value=None):
            r = self.post()
        self.assertEqual(r.status_code, 409)
        self.assertIn("one at a time", r.json()["error"])

    def test_needs_the_ui_header(self):
        self.researched()
        with mock.patch.object(enrich_job, "start_design") as start:
            r = self.post(headers={})
        self.assertEqual(r.status_code, 403)
        start.assert_not_called()


if __name__ == "__main__":
    unittest.main()
