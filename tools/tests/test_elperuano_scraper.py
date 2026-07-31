"""Unit tests for the El Peruano scraper's deterministic stages (no network)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scrapers"))

import elperuano_scraper as er  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class ParseSearchCardsTest(unittest.TestCase):
    """Against a real 2026-07-25 Normas Legales search page (first 4 result cards)."""

    def setUp(self):
        page = (FIXTURES / "elperuano_search_nl.html").read_text(encoding="utf-8")
        self.records = er.parse_search_cards(page, "NL", "2026-07-25")

    def test_parses_every_card_with_all_fields(self):
        self.assertEqual(len(self.records), 4)
        for r in self.records:
            self.assertEqual(
                set(r),
                {"tipo", "numero", "sector", "rubro", "sumilla", "url", "fecha", "op", "tipo_pub"},
            )
            self.assertTrue(r["tipo"] and r["numero"] and r["sumilla"] and r["op"])
            self.assertRegex(r["op"], r"^\d+-\d+$")  # visor/dispositivo id
            self.assertEqual(r["fecha"], "2026-07-25")
            self.assertEqual(r["url"], f"https://busquedas.elperuano.pe/dispositivo/NL/{r['op']}")

    def test_reads_real_norma_fields(self):
        ley = next(r for r in self.records if r["tipo"] == "LEY")
        self.assertEqual(ley["numero"], "N° 32739")
        self.assertIn("escala remunerativa", ley["sumilla"])

    def test_empty_page_is_safe(self):
        self.assertEqual(
            er.parse_search_cards("<html><body>sin resultados</body></html>", "NL", "2026-07-25"), [])


class MatcherIntegrationTest(unittest.TestCase):
    """The scraper matches norma text against the real committed commitment index."""

    def test_matched_ids_are_well_formed_commitments(self):
        import matcher
        ids = matcher.load_matcher().match("Autorizan la creación de unidades de flagrancia")
        self.assertTrue(ids, "a distinctive plan phrase should match at least one commitment")
        self.assertTrue(all(i.count(".") == 1 for i in ids))  # e.g. t1-1.C02

    def test_unrelated_norma_matches_nothing(self):
        import matcher
        self.assertEqual(
            matcher.load_matcher().match("Designan fedatarios institucionales de la intendencia regional"), [])


class NormaTextTest(unittest.TestCase):
    """Against a captured /dispositivo/ page embedding R.M. N° 419-2026-MTC (Hoja de Ruta)."""

    def test_extracts_clean_single_norma_body(self):
        page = (FIXTURES / "elperuano_dispositivo_2538172-1.html").read_bytes()
        text = er.html_to_text(er.extract_visor_html(page))
        self.assertIn("Hoja de Ruta", text)   # this norma's body
        self.assertIn("Que,", text)            # considerandos, not just metadata
        self.assertNotIn("Pataz", text)        # neighboring norma's <title> — <head> stripped
        self.assertNotIn("<", text)            # tags stripped
        self.assertGreater(len(text), 3000)


if __name__ == "__main__":
    unittest.main()
