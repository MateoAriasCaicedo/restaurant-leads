"""Downloads on the Materials tab: one file as an attachment, and a zip of one group or of every group."""
import io
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from starlette.testclient import TestClient

from server import app as server_app
from server import files


def png():
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (4, 4), "red").save(buf, "PNG")
    return buf.getvalue()


class Downloads(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name) / "taco-place-1"
        for kind, names in {"instagram": ["a.png", "b.png"], "maps": ["m.png"], "menu": ["menu.png"], "site": []}.items():
            base = files.folder(self.dir, kind)
            base.mkdir(parents=True)
            for n in names:
                (base / n).write_bytes(png())
        (files.folder(self.dir, "instagram") / "notes.txt").write_text("not a photo")   # not listed, so not zipped
        (self.dir / ".trash").mkdir()
        (self.dir / ".trash" / "instagram-1-old.png").write_bytes(png())

        p = mock.patch.object(server_app, "_lead_dir", lambda key, create=False: self.dir)
        p.start()
        self.addCleanup(p.stop)
        self.client = TestClient(server_app.app, base_url="http://127.0.0.1:8642")

    def names(self, response):
        return sorted(zipfile.ZipFile(io.BytesIO(response.content)).namelist())

    def test_single_file_is_an_attachment(self):
        r = self.client.get("/api/leads/osm-node-1/files/instagram/a.png?download=1")
        self.assertEqual(r.status_code, 200)
        self.assertIn('attachment; filename="a.png"', r.headers["content-disposition"])
        self.assertEqual(r.content, png())

    def test_without_the_flag_the_file_still_opens_inline(self):
        r = self.client.get("/api/leads/osm-node-1/files/instagram/a.png")
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("content-disposition", r.headers)

    def test_download_keeps_the_name_checks(self):
        r = self.client.get("/api/leads/osm-node-1/files/instagram/..%5Cb.png?download=1")
        self.assertEqual(r.status_code, 400)

    def test_zip_of_one_group(self):
        r = self.client.get("/api/leads/osm-node-1/files.zip?kind=instagram")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers["content-type"], "application/zip")
        self.assertIn("taco-place-1-instagram.zip", r.headers["content-disposition"])
        self.assertEqual(int(r.headers["content-length"]), len(r.content))
        self.assertEqual(self.names(r), ["instagram/a.png", "instagram/b.png"])

    def test_zip_of_everything_skips_the_trash(self):
        r = self.client.get("/api/leads/osm-node-1/files.zip")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.names(r), ["instagram/a.png", "instagram/b.png", "maps/m.png", "menu/menu.png"])

    def test_unknown_group_and_empty_group(self):
        self.assertEqual(self.client.get("/api/leads/osm-node-1/files.zip?kind=..").status_code, 400)
        self.assertEqual(self.client.get("/api/leads/osm-node-1/files.zip?kind=site").status_code, 404)


if __name__ == "__main__":
    unittest.main()
