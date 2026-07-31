"""Unit tests for the El Peruano scraper's deterministic stages (no network)."""

import io
import sys
import unittest
import urllib.error
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


class NationalScopeTest(unittest.TestCase):
    """Subnational publishers (municipal/regional own-acts) are out of the review queue."""

    def test_municipal_and_regional_sectors_are_out_of_scope(self):
        for sector in ("MUNICIPALIDAD DE SAN LUIS", "Municipalidad de Ancón",
                       "GOBIERNO REGIONAL DE AMAZONAS", "gobierno regional del cusco"):
            self.assertFalse(er.in_national_scope({"sector": sector}), sector)

    def test_national_sectors_stay_in_scope(self):
        for sector in ("EDUCACIÓN", "COMERCIO EXTERIOR Y TURISMO", "AMBIENTE",
                       "MINISTERIO PÚBLICO", "", "SUPERINTENDENCIA NACIONAL DE SERVICIOS DE SANEAMIENTO"):
            self.assertTrue(er.in_national_scope({"sector": sector}), sector)


class NoiseSuppressionTest(unittest.TestCase):
    """Generic bigrams that flooded the queue are suppressed; real signal survives."""

    def setUp(self):
        import matcher
        self.m = matcher.load_matcher()

    def test_generic_bigrams_no_longer_match(self):
        # Real 2026-07-31 false-positive sumillas that matched only via a generic bigram.
        sumillas = [
            "Aprueban la Sección Segunda del Reglamento de Organización y Funciones del "
            "Servicio Nacional de Meteorología e Hidrología del Perú (SENAMHI)",
            "Aprueban transferencia financiera a favor del Gobierno Regional del "
            "Departamento de Amazonas, para el financiamiento exclusivo de la contrapartida "
            "nacional de diversos proyectos de inversión",
            "Designan Coordinador de las Fiscalías Superiores Penales Nacionales y Fiscalías "
            "Penales Supraprovinciales Especializadas en Derechos Humanos y contra el Terrorismo",
            "Designan Jefa de la Oficina General de Recursos Humanos",
        ]
        for sumilla in sumillas:
            self.assertEqual(self.m.match(sumilla), [], sumilla)

    def test_real_signal_still_matches(self):
        # The distinctive phrase of each affected commitment must still fire.
        self.assertIn("t2-1.P21", self.m.match(
            "Creación del Servicio Nacional de Defensa Jurídica del Emprendedor para "
            "jóvenes emprendedores y MYPES"))
        self.assertIn("t1-4.P01", self.m.match(
            "Modernización del sistema meritocrático liderado por SERVIR"))


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


def _fake_search_page(n: int, base_op: int = 1000) -> str:
    card = (
        '<div class="rounded-xl border bg-card">'
        '<p class="text-sm font-semibold text-primary">SECTOR</p>'
        '<a href="/dispositivo/NL/{op}-1">'
        '<p class="text-xs text-muted-foreground">LEY</p>'
        '<p class="text-xs font-medium text-muted-foreground">N° {op}</p></a>'
        '<a class="line-clamp-3" href="/dispositivo/NL/{op}-1">sumilla {op}</a></div>'
    )
    return "<html><body>" + "".join(card.format(op=base_op + i) for i in range(n)) + "</body></html>"


def _http_error(url: str, code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(url, code, "boom", {}, io.BytesIO(b""))


class DraftNoteTest(unittest.TestCase):
    """The evidence note ships with a draft (the sumilla), never blank."""

    def test_uses_the_sumilla_as_the_draft(self):
        rec = {"tipo": "LEY", "numero": "N° 1", "fecha": "2026-07-28",
               "sumilla": "Ley que crea el registro nacional"}
        self.assertEqual(draft_note := er.draft_note(rec), "Ley que crea el registro nacional.")
        self.assertTrue(draft_note)  # non-blank

    def test_keeps_an_existing_final_period(self):
        rec = {"tipo": "LEY", "numero": "N° 1", "fecha": "2026-07-28", "sumilla": "Aprueban el reglamento."}
        self.assertEqual(er.draft_note(rec), "Aprueban el reglamento.")

    def test_falls_back_when_sumilla_is_empty(self):
        rec = {"tipo": "DECRETO SUPREMO", "numero": "N° 5-2026", "fecha": "2026-07-28", "sumilla": "  "}
        note = er.draft_note(rec)
        self.assertTrue(note)  # never blank
        self.assertIn("DECRETO SUPREMO N° 5-2026", note)

    def test_issue_body_evidence_note_is_never_blank(self):
        rec = {"tipo": "LEY", "numero": "N° 9", "sector": "PCM", "fecha": "2026-07-28",
               "sumilla": "Ley que reforma el sistema",
               "url": "https://busquedas.elperuano.pe/dispositivo/NL/1-1"}
        body = er.issue_body(rec, ["t1-1.P01"], "2026-07-28", excerpt="")
        self.assertIn('"note": "Ley que reforma el sistema."', body)
        self.assertNotIn('"note": ""', body)


class FetchNormasTest(unittest.TestCase):
    """Pagination + transient-error handling, with http_get stubbed (no network)."""

    def setUp(self):
        self._orig_get, self._orig_sleep = er.http_get, er.time.sleep
        er.time.sleep = lambda *a, **k: None  # no real backoff waits

    def tearDown(self):
        er.http_get, er.time.sleep = self._orig_get, self._orig_sleep

    def test_pagination_tail_404_ends_the_edition(self):
        def fake(url):
            if "tipoPublicacion=NL" in url and "start=0" in url:
                return _fake_search_page(er.PAGE_SIZE, 2000).encode()
            if "tipoPublicacion=NL" in url and "start=20" in url:
                raise _http_error(url, 404)  # past the last NL page
            return _fake_search_page(0).encode()  # BO/PC empty
        er.http_get = fake
        self.assertEqual(len(er.fetch_normas("20260101", "2026-01-01")), er.PAGE_SIZE)

    def test_transient_error_is_retried(self):
        calls = {"n": 0}

        def flaky(url):
            if "tipoPublicacion=NL" in url and "start=0" in url:
                calls["n"] += 1
                if calls["n"] == 1:
                    raise _http_error(url, 404)  # one transient blip
                return _fake_search_page(3, 3000).encode()  # then a short page => NL ends
            return _fake_search_page(0).encode()
        er.http_get = flaky
        records = er.fetch_normas("20260101", "2026-01-01")
        self.assertEqual(calls["n"], 2)          # retried once, then succeeded
        self.assertEqual(len(records), 3)

    def test_first_page_404_still_raises(self):
        # a 404 on page 0 is not a pagination tail — it must fail loudly
        er.http_get = lambda url: (_ for _ in ()).throw(_http_error(url, 404))
        with self.assertRaises(urllib.error.HTTPError):
            er.fetch_normas("20260101", "2026-01-01")


if __name__ == "__main__":
    unittest.main()
