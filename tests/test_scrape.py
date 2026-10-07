"""Offline tests for the scrape pipeline (leadgen.enrichment.scrape) and what consumes it.

No browser and no network: Playwright is replaced by small fakes. Run from the repo root:
    python -m unittest discover -s tests -v
"""
import io
import json
import sqlite3
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

from leadgen import config, store
from leadgen.enrichment import scrape
from leadgen.scoring import quality, score

PLACE = {"place_id": "osm:node/1", "name": "Achiote Bistro", "area": "laureles", "address": "Cq. 4 # 71-94",
         "lat": 6.2463, "lng": -75.5912, "website": None, "tags_json": "{}"}
ACCENTS = "Medellín, café, atención, niño"


def jpeg(size=(400, 400)):
    buf = io.BytesIO()
    Image.new("RGB", size, (200, 80, 40)).save(buf, "JPEG")
    return buf.getvalue()


class FakeResponse:
    def __init__(self, status=200, body=b"", payload=None):
        self.status, self._body, self._payload = status, body, payload
        self.ok = 200 <= status < 300

    def body(self):
        return self._body

    def json(self):
        if self._payload is None:
            raise ValueError("not json")
        return self._payload


class FakeCtx:
    """ctx.request.get(url, ...) answers from a {substring: FakeResponse} map; anything else is a 404."""
    def __init__(self, routes):
        self.routes, self.requested = routes, []
        self.request = self

    def get(self, url, **kw):
        self.requested.append(url)
        for key, resp in self.routes.items():
            if key in url:
                return resp
        return FakeResponse(404)


class FakeEl:
    def __init__(self, attrs):
        self.attrs = attrs

    def get_attribute(self, a):
        return self.attrs.get(a)


class FakePage:
    def __init__(self, url="https://www.instagram.com/x/", title="", meta=None):
        self.url, self._title, self.meta = url, title, meta or {}

    def title(self):
        return self._title

    def goto(self, *a, **k):
        pass

    def query_selector(self, sel):
        for prop, content in self.meta.items():
            if prop in sel:
                return FakeEl({"content": content})
        return None


class NoSleep(unittest.TestCase):
    def setUp(self):
        p = mock.patch.object(scrape.time, "sleep")
        p.start()
        self.addCleanup(p.stop)
        self.tmp = Path(tempfile.mkdtemp())


class Pure(unittest.TestCase):
    def test_num_parses_counts(self):
        for raw, want in [("1,234", 1234), ("1.234", 1234), ("12.5K", 12500), ("1,2 mil", 1200), ("3 M", 3000000),
                          ("36", 36), ("\xa01.000", 1000)]:
            self.assertEqual(scrape._num(raw), want, raw)
        self.assertIsNone(scrape._num("n/a"))
        self.assertIsNone(scrape._num(None))

    def test_same_is_accent_and_case_insensitive(self):
        self.assertTrue(scrape._same("Achiote Bistro", "Achiote bistro"))
        self.assertTrue(scrape._same("Café Ñandú", "cafe nandu · Laureles"))
        self.assertFalse(scrape._same("Achiote Bistro", "Hamburguesas El Corral"))
        self.assertFalse(scrape._same("Achiote", None))
        self.assertFalse(scrape._same("", "anything"))

    def test_instagram_handle_sources(self):
        p = {"website": None}
        self.assertEqual(scrape.instagram_handle(p, {"contact:instagram": "https://www.instagram.com/achiote.bistro/"}, {}), "achiote.bistro")
        self.assertEqual(scrape.instagram_handle(p, {"instagram": "@achiote_bistro"}, {}), "achiote_bistro")
        self.assertEqual(scrape.instagram_handle({"website": "https://instagram.com/foo"}, {}, {}), "foo")
        self.assertEqual(scrape.instagram_handle(p, {}, {"social": ["https://facebook.com/x", "https://instagram.com/bar?hl=es"]}), "bar")
        self.assertIsNone(scrape.instagram_handle(p, {}, {}))

    def test_instagram_handle_rejects_non_profile_paths(self):
        for path in ("p", "reel", "explore", "accounts", "stories", "tv"):
            self.assertIsNone(scrape.instagram_handle({"website": f"https://instagram.com/{path}/abc"}, {}, {}), path)


class Photos(NoSleep):
    def test_save_photo_converts_to_jpeg(self):
        buf = io.BytesIO()
        Image.new("RGBA", (500, 500), (1, 2, 3, 128)).save(buf, "PNG")
        dest = self.tmp / "a.jpg"
        self.assertTrue(scrape._save_photo(buf.getvalue(), dest))
        with Image.open(dest) as im:
            self.assertEqual(im.format, "JPEG")

    def test_save_photo_rejects_junk_and_tiny_images(self):
        self.assertFalse(scrape._save_photo(b"<html>blocked</html>", self.tmp / "a.jpg"))
        self.assertFalse(scrape._save_photo(jpeg((100, 100)), self.tmp / "b.jpg"))      # icons / avatars
        self.assertFalse((self.tmp / "a.jpg").exists())

    def test_save_photo_shrinks_large_images(self):
        dest = self.tmp / "big.jpg"
        self.assertTrue(scrape._save_photo(jpeg((4000, 3000)), dest))
        with Image.open(dest) as im:
            self.assertLessEqual(max(im.size), config.MAX_IMAGE_PX)

    def test_download_replaces_old_scrapes_but_keeps_user_files(self):
        folder = self.tmp / "maps"
        folder.mkdir()
        (folder / "scrape-01.jpg").write_bytes(b"old")
        (folder / "mine.jpg").write_bytes(b"user drop-in")
        ctx = FakeCtx({"good": FakeResponse(body=jpeg()), "bad": FakeResponse(body=b"nope")})
        saved = scrape._download(ctx, ["http://x/bad1", "http://x/good1", "http://x/good1", "http://x/good2"], folder, 10)
        self.assertEqual(saved, ["scrape-01.jpg", "scrape-02.jpg"])          # junk skipped, duplicate url fetched once
        self.assertEqual((folder / "mine.jpg").read_bytes(), b"user drop-in")
        self.assertGreater((folder / "scrape-01.jpg").stat().st_size, 3)       # the stale file was replaced
        self.assertEqual(len([u for u in ctx.requested if u.endswith("good1")]), 1)

    def test_download_respects_limit(self):
        ctx = FakeCtx({"good": FakeResponse(body=jpeg())})
        saved = scrape._download(ctx, [f"http://x/good{i}" for i in range(6)], self.tmp / "ig", 2)
        self.assertEqual(len(saved), 2)


class BlockDetection(unittest.TestCase):
    def test_captcha_and_unusual_traffic_raise_blocked(self):
        for url, title in [("https://www.google.com/sorry/index", ""), ("https://maps.google.com/", "Unusual traffic from your network"),
                           ("https://x/", "Tráfico inusual"), ("https://x/captcha", "")]:
            with self.assertRaises(scrape.Blocked, msg=url + title):
                scrape._check_block(FakePage(url=url, title=title))

    def test_normal_page_passes(self):
        scrape._check_block(FakePage(url="https://www.google.com/maps/place/Achiote", title="Achiote bistro - Google Maps"))


class Instagram(NoSleep):
    def user_payload(self):
        return {"data": {"user": {
            "full_name": "Achiote", "biography": "Cocina de autor en Laureles", "external_url": "https://achiote.co",
            "category_name": "Restaurant", "is_private": False,
            "edge_followed_by": {"count": 1200}, "edge_follow": {"count": 90},
            "edge_owner_to_timeline_media": {"count": 2, "edges": [
                {"node": {"taken_at_timestamp": 1700000000, "edge_media_to_caption": {"edges": [{"node": {"text": "Nuevo menú"}}]},
                          "edge_liked_by": {"count": 10}, "edge_media_to_comment": {"count": 1}, "is_video": False,
                          "display_url": "http://cdn/p1"}},
                {"node": {"taken_at_timestamp": 1710000000, "edge_media_to_caption": {"edges": []},
                          "edge_liked_by": {"count": 5}, "edge_media_to_comment": {"count": 0}, "is_video": True,
                          "display_url": None}}]}}}}

    def test_api_profile_is_parsed(self):
        ctx = FakeCtx({"web_profile_info": FakeResponse(payload=self.user_payload()), "cdn/p1": FakeResponse(body=jpeg())})
        out = scrape.scrape_instagram(FakePage(), ctx, "achiote", self.tmp)
        self.assertEqual(out["status"], "ok")
        self.assertEqual((out["followers"], out["following"], out["post_count"]), (1200, 90, 2))
        self.assertEqual(out["last_post"], "2024-03-09")
        self.assertEqual(out["posts"][0]["caption"], "Nuevo menú")
        self.assertEqual(out["posts"][1]["caption"], "")
        self.assertTrue(all("image" not in p for p in out["posts"]))        # image urls are not persisted
        self.assertEqual(out["photos"], ["scrape-01.jpg"])

    def test_404_is_not_found(self):
        out = scrape.scrape_instagram(FakePage(), FakeCtx({"web_profile_info": FakeResponse(404)}), "ghost", self.tmp)
        self.assertEqual(out, {"status": "not_found", "handle": "ghost"})

    def test_login_wall_is_blocked_and_nothing_is_read(self):
        page = FakePage(url="https://www.instagram.com/accounts/login/?next=/x/")
        out = scrape.scrape_instagram(page, FakeCtx({"web_profile_info": FakeResponse(429)}), "x", self.tmp)
        self.assertEqual(out["status"], "blocked")
        self.assertNotIn("followers", out)

    def test_no_meta_tags_is_blocked(self):
        out = scrape.scrape_instagram(FakePage(), FakeCtx({"web_profile_info": FakeResponse(429)}), "x", self.tmp)
        self.assertEqual(out["status"], "blocked")

    def test_meta_preview_fallback_reads_counts(self):
        page = FakePage(meta={"og:title": "Achiote Bistro (@achiote) • Instagram photos",
                              "og:description": "1,234 Followers, 56 Following, 78 Posts - Cocina de autor"})
        out = scrape.scrape_instagram(page, FakeCtx({"web_profile_info": FakeResponse(429)}), "achiote", self.tmp)
        self.assertEqual(out["status"], "ok")
        self.assertEqual((out["followers"], out["following"], out["post_count"]), (1234, 56, 78))
        self.assertEqual(out["full_name"], "Achiote Bistro")
        self.assertEqual(out["posts"], [])

    def test_captcha_page_raises_blocked(self):
        with self.assertRaises(scrape.Blocked):
            scrape.scrape_instagram(FakePage(title="captcha"), FakeCtx({"web_profile_info": FakeResponse(429)}), "x", self.tmp)


def fake_playwright():
    """A stand-in for playwright.sync_api whose browser does nothing."""
    browser = mock.MagicMock()
    pw = mock.MagicMock()
    pw.chromium.launch.return_value = browser
    cm = mock.MagicMock()
    cm.__enter__.return_value = pw
    mod = types.ModuleType("playwright.sync_api")
    mod.sync_playwright = lambda: cm
    return mod, browser


class Collect(NoSleep):
    """scrape.collect(): orchestration, error isolation, scrape.json, place_quality."""
    def setUp(self):
        super().setUp()
        self.d = self.tmp / "lead"
        p = mock.patch.object(config, "DB_PATH", str(self.tmp / "t.db"))
        p.start()
        self.addCleanup(p.stop)
        mod, self.browser = fake_playwright()
        p = mock.patch.dict(sys.modules, {"playwright": types.ModuleType("playwright"), "playwright.sync_api": mod})
        p.start()
        self.addCleanup(p.stop)

    def run_collect(self, maps=None, ig=None, tags=None, sources=scrape.SOURCES):
        def pick(result):
            def f(*a, **k):
                if isinstance(result, Exception):
                    raise result
                return result
            return f
        with mock.patch.object(scrape, "scrape_maps", pick(maps)), mock.patch.object(scrape, "scrape_instagram", pick(ig)):
            return scrape.collect(PLACE, tags or {}, {}, self.d, sources, log=lambda *_: None)

    def written(self):
        return json.loads((self.d / "profile" / "scrape.json").read_text("utf-8"))

    def test_blocked_source_is_recorded_and_the_other_still_runs(self):
        res = self.run_collect(maps=scrape.Blocked("captcha"), ig={"status": "ok", "handle": "a"}, tags={"instagram": "a"})
        self.assertEqual(res["maps"]["status"], "blocked")
        self.assertEqual(res["instagram"]["status"], "ok")
        self.browser.close.assert_called_once()

    def test_unexpected_error_is_recorded_not_raised(self):
        res = self.run_collect(maps=TimeoutError("page took too long"), sources=("maps",))
        self.assertEqual(res["maps"]["status"], "error")
        self.assertIn("TimeoutError", res["maps"]["note"])
        self.browser.close.assert_called_once()

    def test_instagram_without_handle_is_no_handle(self):
        res = self.run_collect(maps={"status": "not_found", "note": "No results."})
        self.assertEqual(res["instagram"]["status"], "no_handle")

    def test_scrape_json_keeps_accents_as_utf8(self):
        self.run_collect(maps={"status": "ok", "name": "Achiote", "name_match": True, "rating": 4.2, "address": ACCENTS, "photos": []},
                         sources=("maps",))
        raw = (self.d / "profile" / "scrape.json").read_bytes()
        self.assertIn(ACCENTS.encode("utf-8"), raw)           # literal UTF-8, not \u escapes or replacement characters
        self.assertNotIn("�".encode("utf-8"), raw)
        self.assertEqual(self.written()["maps"]["address"], ACCENTS)

    def test_rescrape_removes_stale_photos_but_not_user_files(self):
        folder = self.d / "photos" / "maps"
        folder.mkdir(parents=True)
        (folder / "scrape-01.jpg").write_bytes(b"stale")
        (folder / "menu-from-owner.jpg").write_bytes(b"mine")
        self.run_collect(maps={"status": "no_match", "note": "x"}, sources=("maps",))
        self.assertFalse((folder / "scrape-01.jpg").exists())
        self.assertTrue((folder / "menu-from-owner.jpg").exists())

    def test_verified_maps_result_is_recorded_for_quality(self):
        self.run_collect(maps={"status": "ok", "name": "Achiote", "name_match": True, "rating": 4.5, "review_count": 80,
                               "category": "Restaurante", "closed_flag": None, "photos": []}, sources=("maps",))
        row = quality.load(store.connect())["osm:node/1"]
        self.assertEqual((row["rating"], row["review_count"], row["closed_flag"]), (4.5, 80, None))

    def test_unverified_maps_result_is_not_recorded(self):
        self.run_collect(maps={"status": "ok", "name": "Other", "name_match": False, "rating": 4.9, "review_count": 500},
                         sources=("maps",))
        self.assertEqual(quality.load(store.connect()), {})


class ContextSection(unittest.TestCase):
    def test_not_requested(self):
        self.assertIn("not collected", "\n".join(scrape.context_section(None)))

    def test_failed_sources_say_why(self):
        out = "\n".join(scrape.context_section({"scraped_at": "now", "maps": {"status": "blocked", "note": "captcha"},
                                                 "instagram": {"status": "no_handle", "note": "No link"}}))
        self.assertIn("Google Maps: blocked captcha", out)
        self.assertIn("Instagram: no_handle", out)

    def test_ok_sources_render_details_and_closed_flag(self):
        res = {"scraped_at": "now",
               "maps": {"status": "ok", "name": "Achiote", "rating": 3.6, "review_count": 36, "category": "Café", "name_match": True,
                        "closed_flag": "permanently closed", "address": ACCENTS, "phone": "1", "website": None, "url": "u",
                        "hours": [], "photos": ["a"], "reviews": [{"stars": 5, "when": "hace un mes", "text": "Excelente atención"}]},
               "instagram": {"status": "ok", "handle": "a", "followers": 10, "post_count": 3, "photos": [],
                             "posts": [{"date": "2024-01-01", "likes": 2, "caption": "hola"}]}}
        out = "\n".join(scrape.context_section(res))
        for needle in ("permanently closed", "rating 3.6 from 36 reviews", ACCENTS, "Excelente atención", "@a: 10 followers"):
            self.assertIn(needle, out)


def db_with_place(**over):
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.execute("""CREATE TABLE places (
        place_id TEXT PRIMARY KEY, area TEXT, name TEXT, address TEXT, lat REAL, lng REAL, rating REAL, review_count INTEGER,
        price_level TEXT, website TEXT, phone TEXT, status TEXT, primary_type TEXT, types TEXT, maps_url TEXT, reviews_json TEXT,
        has_hours INTEGER, fetched_at REAL, tags_json TEXT)""")
    row = dict(place_id="osm:node/1", area="laureles", name="Achiote Bistro", address="Cq. 4", lat=6.24, lng=-75.59, rating=None,
               review_count=None, price_level=None, website=None, phone="315", status=None, primary_type="restaurant",
               types="[]", maps_url="", reviews_json="[]", has_hours=1, fetched_at=0, tags_json="{}")
    row.update(over)
    con.execute(f"INSERT INTO places VALUES ({','.join('?' * len(row))})", tuple(row.values()))
    return con


class ClosedPlaces(unittest.TestCase):
    """A restaurant Maps reports as permanently closed must never be ranked as a lead."""
    def maps(self, flag):
        return {"rating": 3.6, "review_count": 36, "category": None, "closed_flag": flag}

    def test_excluded_only_when_permanently_closed(self):
        p = db_with_place().execute("SELECT * FROM places").fetchone()
        self.assertIsNone(score.excluded(p))
        self.assertIsNone(score.excluded(p, self.maps(None)))
        self.assertIsNone(score.excluded(p, self.maps("temporarily closed")))
        self.assertEqual(score.excluded(p, self.maps("permanently closed")), "permanently closed")

    def test_ranked_drops_closed_place_and_reports_it(self):
        con = db_with_place()
        rows, _, _ = score.ranked(con)
        self.assertEqual(len(rows), 1)
        quality.record(con, "osm:node/1", {"status": "ok", "name_match": True, **self.maps("permanently closed")})
        rows, skipped, hidden = score.ranked(con, include_excluded=True)
        self.assertEqual(rows, [])
        self.assertEqual(skipped, {"permanently closed": 1})
        self.assertEqual(hidden[0]["excluded_reason"], "permanently closed")

    def test_closed_listing_without_rating_is_still_recorded(self):
        con = db_with_place()
        self.assertTrue(quality.record(con, "osm:node/1", {"status": "ok", "name_match": True, "rating": None,
                                                           "closed_flag": "permanently closed"}))
        rows, skipped, _ = score.ranked(con)
        self.assertEqual((rows, skipped), ([], {"permanently closed": 1}))

    def test_record_ignores_unverified_results(self):
        con = db_with_place()
        for bad in (None, {"status": "blocked"}, {"status": "ok", "name_match": False, "rating": 4},
                    {"status": "ok", "name_match": True, "rating": None, "closed_flag": None}):
            self.assertFalse(quality.record(con, "osm:node/1", bad), bad)
        self.assertEqual(quality.load(con), {})

    def test_closed_maps_data_gives_no_premium_tier(self):
        p = db_with_place().execute("SELECT * FROM places").fetchone()
        q = quality.evaluate(p, {}, self.maps("permanently closed") | {"rating": 4.9, "review_count": 900})
        self.assertEqual(q["source"], "osm")


if __name__ == "__main__":
    unittest.main()
