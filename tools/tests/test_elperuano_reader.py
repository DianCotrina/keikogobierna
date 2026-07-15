"""Unit tests for the El Peruano reader's deterministic stages (no network)."""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scrapers"))

import elperuano_reader as er  # noqa: E402
from watcher_common import dedup_token  # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "graphql_sample.json"


class ParseResultsTest(unittest.TestCase):
    def test_maps_fixture_hits_and_detects_next_page(self):
        payload = json.loads(FIXTURE.read_text())
        records, has_next = er.parse_results(payload)
        self.assertEqual(len(records), len(payload["data"]["results"]["hits"]))
        self.assertTrue(has_next)  # fixture captured with paginatedBy < totalHits
        first = records[0]
        self.assertEqual(set(first), {"tipo", "numero", "sector", "rubro", "sumilla", "url_pdf", "fecha"})
        self.assertTrue(all(isinstance(v, str) for v in first.values()))

    def test_empty_payload_is_safe(self):
        records, has_next = er.parse_results({})
        self.assertEqual(records, [])
        self.assertFalse(has_next)


class MatchRecordTest(unittest.TestCase):
    KEYWORDS = [
        {"query": "patrulleros inteligentes cámaras comisarías", "related": ["t1-1.C04"]},
        {"query": "MYPE formalización trámites digitales", "related": ["t2-1.C01"]},
    ]

    def test_matches_on_sumilla_terms(self):
        rec = {
            "numero": "N° 044-2026-IN", "tipo": "Decreto Supremo", "sumilla":
            "Autorizan la adquisición de patrulleros inteligentes con cámaras para comisarías",
        }
        self.assertEqual(er.match_record(rec, self.KEYWORDS), ["t1-1.C04"])

    def test_no_match_returns_empty(self):
        rec = {"numero": "N° 1", "tipo": "Ordenanza", "sumilla": "Aprueban horario de feria dominical"}
        self.assertEqual(er.match_record(rec, self.KEYWORDS), [])

    def test_accent_and_case_insensitive(self):
        rec = {"numero": "X", "tipo": "Ley", "sumilla": "FORMALIZACION de la MYPE con tramites DIGITALES"}
        self.assertEqual(er.match_record(rec, self.KEYWORDS), ["t2-1.C01"])


class HelpersTest(unittest.TestCase):
    def test_significant_terms_drops_stopwords_and_short(self):
        self.assertEqual(er.significant_terms("de la MYPE en el Perú"), ["mype", "peru"])

    def test_dedup_token_stable(self):
        key = "Ley|N° 31234|2026-07-10"
        self.assertEqual(dedup_token("np", key), dedup_token("np", key))
        self.assertTrue(dedup_token("np", key).startswith("np-"))


if __name__ == "__main__":
    unittest.main()
