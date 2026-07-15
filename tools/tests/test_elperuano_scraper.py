"""Unit tests for the El Peruano scraper's deterministic stages (no network)."""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scrapers"))

import elperuano_scraper as er  # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "graphql_sample.json"


class ParseResultsTest(unittest.TestCase):
    def test_maps_fixture_hits_and_detects_next_page(self):
        payload = json.loads(FIXTURE.read_text())
        records, has_next = er.parse_results(payload)
        self.assertEqual(len(records), len(payload["data"]["results"]["hits"]))
        self.assertTrue(has_next)  # fixture captured with paginatedBy < totalHits
        first = records[0]
        self.assertEqual(set(first), {"tipo", "numero", "sector", "rubro", "sumilla", "url_pdf", "fecha", "op"})
        self.assertTrue(all(isinstance(v, str) for v in first.values()))
        self.assertRegex(first["op"], r"^\d+-\d+$")  # visor_html/dispositivo id

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


class HtmlToTextTest(unittest.TestCase):
    """Against the captured real /api/visor_html rendition of R. Leg. N° 32726."""

    VISOR_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "visor_html_2535114-1.html"

    def test_extracts_full_single_norma_body(self):
        text = er.html_to_text(self.VISOR_FIXTURE.read_bytes())
        self.assertIn("Southern Vanguard", text)   # body, not just metadata
        self.assertIn("Artículo 1", text)
        self.assertIn("32726", text)
        self.assertNotIn("32727", text)            # no bleed into the neighboring norma
        self.assertNotIn("Texto Integrado del Reglamento", text)  # <head> title noise stripped
        self.assertNotIn("<", text)                # tags stripped
        self.assertGreater(len(text), 3000)


if __name__ == "__main__":
    unittest.main()
