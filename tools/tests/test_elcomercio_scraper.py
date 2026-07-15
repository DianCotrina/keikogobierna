"""Unit tests for the El Comercio scraper's deterministic stages (no network)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scrapers"))

import elcomercio_scraper as ec

FIXTURE = (Path(__file__).resolve().parent / "fixtures" / "elcomercio_rss_sample.xml").read_bytes()


class CanonicalUrlTest(unittest.TestCase):
    def test_strips_query_and_fragment(self):
        self.assertEqual(
            ec.canonical_url("https://elcomercio.pe/politica/nota/?ref=rss&outputType=xml#top"),
            "https://elcomercio.pe/politica/nota/",
        )

    def test_plain_url_unchanged(self):
        self.assertEqual(ec.canonical_url("https://elcomercio.pe/politica/nota/"),
                         "https://elcomercio.pe/politica/nota/")


class ParseFeedTest(unittest.TestCase):
    def test_maps_all_items_with_expected_fields(self):
        items = ec.parse_feed(FIXTURE)
        self.assertEqual(len(items), 5)
        self.assertEqual(set(items[0]), {"title", "url", "summary", "author", "published"})

    def test_canonicalizes_link_and_parses_date(self):
        first = ec.parse_feed(FIXTURE)[0]
        self.assertEqual(first["url"], "https://elcomercio.pe/politica/fuerza-popular-evaluara-auditoria-noticia/")
        self.assertEqual(first["published"], "2026-07-15T05:01:00-05:00")
        self.assertEqual(first["author"], "Redacción EC")

    def test_missing_creator_and_description_default_to_empty(self):
        items = ec.parse_feed(FIXTURE)
        self.assertEqual(items[1]["author"], "")
        self.assertEqual(items[4]["summary"], "")


class MatchTest(unittest.TestCase):
    def test_fixture_matches_title_and_description(self):
        items = ec.parse_feed(FIXTURE)
        matched = [i for i in items if ec.item_matches(i)]
        self.assertEqual(len(matched), 4)  # items 1, 2, 4 (dup), 5 — not the Vásquez one

    def test_case_and_accent_insensitive(self):
        self.assertTrue(ec.item_matches({"title": "El FUJIMORISMO en el Congreso", "summary": ""}))
        self.assertTrue(ec.item_matches({"title": "Análisis", "summary": "La postura de Fuerza Popular"}))

    def test_unrelated_item_does_not_match(self):
        self.assertFalse(ec.item_matches({"title": "Temblor en Lima esta madrugada", "summary": "IGP reportó 4.5"}))


class MergeTest(unittest.TestCase):
    def test_dedupes_by_canonical_url_and_sorts_desc(self):
        items = [i for i in ec.parse_feed(FIXTURE) if ec.item_matches(i)]
        merged = ec.merge_history([], items, "2026-07-15T12:00:00+00:00")
        self.assertEqual(len(merged), 3)  # the ?ref= duplicate collapsed
        self.assertEqual([a["published"] for a in merged],
                         ["2026-07-15T05:01:00-05:00", "2026-07-14T18:12:00-05:00", "2026-07-14T09:00:00-05:00"])
        self.assertTrue(all(a["captured"] == "2026-07-15T12:00:00+00:00" for a in merged))

    def test_existing_entry_wins_and_keeps_captured(self):
        existing = [{"title": "old", "url": "https://elcomercio.pe/politica/nota/",
                     "summary": "", "author": "", "published": "2026-07-14T10:00:00-05:00",
                     "captured": "2026-07-14T16:00:00+00:00"}]
        new = [{"title": "new crawl of same nota", "url": "https://elcomercio.pe/politica/nota/",
                "summary": "", "author": "", "published": "2026-07-14T10:00:00-05:00"}]
        merged = ec.merge_history(existing, new, "2026-07-15T12:00:00+00:00")
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["title"], "old")
        self.assertEqual(merged[0]["captured"], "2026-07-14T16:00:00+00:00")


class TodayTest(unittest.TestCase):
    def test_selects_latest_lima_day(self):
        items = [i for i in ec.parse_feed(FIXTURE) if ec.item_matches(i)]
        merged = ec.merge_history([], items, "2026-07-15T12:00:00+00:00")
        day, day_articles = ec.select_today(merged)
        self.assertEqual(day, "2026-07-15")
        self.assertEqual(len(day_articles), 1)

    def test_utc_timestamps_bucket_to_lima_days(self):
        arts = [
            {"url": "a", "published": "2026-07-15T04:30:00+00:00"},  # 23:30 Jul 14 in Lima
            {"url": "b", "published": "2026-07-15T13:00:00+00:00"},  # 08:00 Jul 15 in Lima
        ]
        day, day_articles = ec.select_today(arts)
        self.assertEqual(day, "2026-07-15")
        self.assertEqual([a["url"] for a in day_articles], ["b"])

    def test_empty_history_is_safe(self):
        self.assertEqual(ec.select_today([]), ("", []))


if __name__ == "__main__":
    unittest.main()
