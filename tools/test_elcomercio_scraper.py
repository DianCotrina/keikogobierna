"""Unit tests for the El Comercio scraper's deterministic stages (no network)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

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


if __name__ == "__main__":
    unittest.main()
