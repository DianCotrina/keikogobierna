"""Unit tests for the ultimitas scraper's deterministic stages (no network)."""

import unittest
from datetime import datetime
from pathlib import Path


from tools.scrapers import ultimitas_scraper as us
from tools.scrapers.common import press_feeds

FIXTURE = (Path(__file__).resolve().parent / "fixtures" / "elcomercio_rss_sample.xml").read_bytes()


class CanonicalUrlTest(unittest.TestCase):
    def test_strips_query_and_fragment(self):
        self.assertEqual(
            us.canonical_url("https://elcomercio.pe/politica/nota/?ref=rss&outputType=xml#top"),
            "https://elcomercio.pe/politica/nota/",
        )

    def test_plain_url_unchanged(self):
        self.assertEqual(us.canonical_url("https://elcomercio.pe/politica/nota/"),
                         "https://elcomercio.pe/politica/nota/")


class ParseFeedTest(unittest.TestCase):
    def test_maps_all_items_with_expected_fields(self):
        items = us.parse_feed(FIXTURE, "El Comercio")
        self.assertEqual(len(items), 5)
        self.assertEqual(set(items[0]), {"title", "url", "summary", "author", "published", "source"})

    def test_stamps_the_given_source_on_every_item(self):
        items = us.parse_feed(FIXTURE, "El Comercio")
        self.assertTrue(all(i["source"] == "El Comercio" for i in items))

    def test_canonicalizes_link_and_parses_date(self):
        first = us.parse_feed(FIXTURE, "El Comercio")[0]
        self.assertEqual(first["url"], "https://elcomercio.pe/politica/fuerza-popular-evaluara-auditoria-noticia/")
        self.assertEqual(first["published"], "2026-07-15T05:01:00-05:00")
        self.assertEqual(first["author"], "Redacción EC")

    def test_missing_creator_and_description_default_to_empty(self):
        items = us.parse_feed(FIXTURE, "El Comercio")
        self.assertEqual(items[1]["author"], "")
        self.assertEqual(items[4]["summary"], "")


class MatchTest(unittest.TestCase):
    def test_fixture_matches_title_and_description(self):
        items = us.parse_feed(FIXTURE, "El Comercio")
        matched = [i for i in items if us.item_matches(i)]
        self.assertEqual(len(matched), 4)  # items 1, 2, 4 (dup), 5 — not the Vásquez one

    def test_case_and_accent_insensitive(self):
        self.assertTrue(us.item_matches({"title": "El FUJIMORISMO en el Congreso", "summary": ""}))
        self.assertTrue(us.item_matches({"title": "Análisis", "summary": "La postura de Fuerza Popular"}))

    def test_unrelated_item_does_not_match(self):
        self.assertFalse(us.item_matches({"title": "Temblor en Lima esta madrugada", "summary": "IGP reportó 4.5"}))


class MergeTest(unittest.TestCase):
    def test_dedupes_by_canonical_url_and_sorts_desc(self):
        items = [i for i in us.parse_feed(FIXTURE, "El Comercio") if us.item_matches(i)]
        merged = us.merge_history([], items, "2026-07-15T12:00:00+00:00")
        self.assertEqual(len(merged), 3)  # the ?ref= duplicate collapsed
        self.assertEqual([a["published"] for a in merged],
                         ["2026-07-15T05:01:00-05:00", "2026-07-14T18:12:00-05:00", "2026-07-14T09:00:00-05:00"])
        self.assertTrue(all(a["captured"] == "2026-07-15T12:00:00+00:00" for a in merged))

    def test_existing_entry_wins_and_keeps_captured(self):
        existing = [{"title": "old", "url": "https://elcomercio.pe/politica/nota/",
                     "summary": "", "author": "", "published": "2026-07-14T10:00:00-05:00",
                     "source": "El Comercio", "captured": "2026-07-14T16:00:00+00:00"}]
        new = [{"title": "new crawl of same nota", "url": "https://elcomercio.pe/politica/nota/",
                "summary": "", "author": "", "published": "2026-07-14T10:00:00-05:00",
                "source": "El Comercio"}]
        merged = us.merge_history(existing, new, "2026-07-15T12:00:00+00:00")
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["title"], "old")
        self.assertEqual(merged[0]["captured"], "2026-07-14T16:00:00+00:00")


class TodayTest(unittest.TestCase):
    def test_selects_latest_lima_day(self):
        items = [i for i in us.parse_feed(FIXTURE, "El Comercio") if us.item_matches(i)]
        merged = us.merge_history([], items, "2026-07-15T12:00:00+00:00")
        day, day_articles = us.select_today(merged)
        self.assertEqual(day, "2026-07-15")
        self.assertEqual(len(day_articles), 1)

    def test_utc_timestamps_bucket_to_lima_days(self):
        arts = [
            {"url": "a", "published": "2026-07-15T04:30:00+00:00"},  # 23:30 Jul 14 in Lima
            {"url": "b", "published": "2026-07-15T13:00:00+00:00"},  # 08:00 Jul 15 in Lima
        ]
        day, day_articles = us.select_today(arts)
        self.assertEqual(day, "2026-07-15")
        self.assertEqual([a["url"] for a in day_articles], ["b"])

    def test_empty_history_is_safe(self):
        self.assertEqual(us.select_today([]), ("", []))


LR_FIXTURE = (Path(__file__).resolve().parent / "fixtures" / "larepublica_rss_sample.xml").read_bytes()


class LaRepublicaFeedTest(unittest.TestCase):
    """Structural assertions against a captured slice of the real feed —
    exact strings vary with the news cycle, the shape must not."""

    def test_real_feed_slice_parses_with_all_fields(self):
        items = us.parse_feed(LR_FIXTURE, "La República")
        self.assertGreater(len(items), 0)
        for item in items:
            self.assertEqual(set(item), {"title", "url", "summary", "author", "published", "source"})
            self.assertTrue(item["title"])
            self.assertTrue(item["url"].startswith("https://larepublica.pe/"))
            datetime.fromisoformat(item["published"])  # raises if unparseable
            self.assertEqual(item["source"], "La República")

    def test_every_outlet_is_configured(self):
        names = [s["name"] for s in us.SOURCES]
        for outlet in ("El Comercio", "La República", "RPP", "Gestión"):
            self.assertIn(outlet, names)

    def test_source_names_are_unique(self):
        # The ultimitas page derives its filter chips from these names.
        names = [s["name"] for s in us.SOURCES]
        self.assertEqual(len(names), len(set(names)))


class SourceIsolationTest(unittest.TestCase):
    def test_one_dead_source_does_not_kill_the_other(self):
        # fetch_sources lives in the shared feed layer, so that is where the
        # transport seam is: /ultimitas/ and cabinet_scraper --press both get
        # this isolation from the same code.
        real_http_get = press_feeds.http_get

        def stub(url, headers=None):
            if "larepublica" in url:
                raise OSError("simulated outage")
            return FIXTURE

        press_feeds.http_get = stub
        try:
            items, failed = press_feeds.fetch_sources()
        finally:
            press_feeds.http_get = real_http_get
        self.assertEqual(failed, ["La República"])
        self.assertTrue(items)  # the other outlets still delivered
        self.assertNotIn("La República", {i["source"] for i in items})


if __name__ == "__main__":
    unittest.main()


INFOBAE_FIXTURE = (Path(__file__).resolve().parent / "fixtures" / "infobae_peru_20260728.xml").read_bytes()


class InfobaeFeedTest(unittest.TestCase):
    def test_infobae_is_configured(self):
        self.assertIn("Infobae", [s["name"] for s in us.SOURCES])

    def test_real_feed_slice_parses_with_all_fields(self):
        items = us.parse_feed(INFOBAE_FIXTURE, "Infobae")
        self.assertGreater(len(items), 50)
        for item in items:
            self.assertEqual(set(item), {"title", "url", "summary", "author", "published", "source"})
            self.assertTrue(item["title"])
            self.assertTrue(item["url"].startswith("https://"))
            self.assertEqual(item["source"], "Infobae")

    def test_summaries_carry_the_biographical_detail(self):
        # The whole point: profession sits in the feed's own description, so no
        # article body ever needs reading.
        items = us.parse_feed(INFOBAE_FIXTURE, "Infobae")
        self.assertTrue(any(len(i["summary"]) > 80 for i in items))
