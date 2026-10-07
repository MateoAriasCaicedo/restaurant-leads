"""The Pipeline page's maintenance buttons: POST /api/jobs/maintenance maps each task to the right script and flags."""
import unittest
from unittest import mock

from starlette.testclient import TestClient

from server import app as server_app
from server import jobs

HEADERS = {"X-Leads-UI": "1", "Origin": "http://127.0.0.1:8642"}


class Maintenance(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(server_app.app, base_url="http://127.0.0.1:8642")
        self.started = []

        def fake(kind, title, argv, params, lead=None, failure=""):
            self.started.append((kind, argv[2:]))
            return jobs.Job(kind, title, "pipeline", params, lead)

        p = mock.patch.object(jobs, "_script_job", fake)
        p.start()
        self.addCleanup(p.stop)

    def test_each_task_runs_its_script(self):
        want = {"find_sites": ["audit.py", "--discover"], "pagespeed": ["audit.py", "--perf"],
                "rescore": ["audit.py", "--rescore"], "backfill": ["quality.py", "--backfill"]}
        for task, argv in want.items():
            r = self.client.post("/api/jobs/maintenance", json={"task": task}, headers=HEADERS)
            self.assertEqual(r.status_code, 202, task)
            self.assertEqual(r.json()["job"]["kind"], task)
            self.assertIn((task, argv), self.started)

    def test_unknown_task_is_rejected(self):
        for body in ({"task": "rm -rf"}, {}, {"task": None}):
            r = self.client.post("/api/jobs/maintenance", json=body, headers=HEADERS)
            self.assertEqual(r.status_code, 400, body)
        self.assertEqual(self.started, [])

    def test_post_needs_the_ui_header(self):
        self.assertEqual(self.client.post("/api/jobs/maintenance", json={"task": "rescore"}).status_code, 403)
        self.assertEqual(self.started, [])


if __name__ == "__main__":
    unittest.main()
