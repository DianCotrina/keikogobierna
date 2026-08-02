"""Unit tests for the El Peruano scraper's deterministic stages (no network)."""

import io
import sys
import unittest
import urllib.error
from pathlib import Path


from tools.scrapers import elperuano_scraper as er  # noqa: E402
from tools.scrapers.common import elperuano_client as ec  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class ParseSearchCardsTest(unittest.TestCase):
    """Against a real 2026-07-25 Normas Legales search page (first 4 result cards)."""

    def setUp(self):
        page = (FIXTURES / "elperuano_search_nl.html").read_text(encoding="utf-8")
        self.records = ec.parse_search_cards(page, "NL", "2026-07-25")

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
            ec.parse_search_cards("<html><body>sin resultados</body></html>", "NL", "2026-07-25"), [])


class MatcherIntegrationTest(unittest.TestCase):
    """The scraper matches norma text against the real committed commitment index."""

    def test_matched_ids_are_well_formed_commitments(self):
        from tools.scrapers.common import matcher
        ids = matcher.load_matcher().match("Autorizan la creación de unidades de flagrancia")
        self.assertTrue(ids, "a distinctive plan phrase should match at least one commitment")
        self.assertTrue(all(i.count(".") == 1 for i in ids))  # e.g. t1-1.C02

    def test_unrelated_norma_matches_nothing(self):
        from tools.scrapers.common import matcher
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
                       "", "SUPERINTENDENCIA NACIONAL DE SERVICIOS DE SANEAMIENTO"):
            self.assertTrue(er.in_national_scope({"sector": sector}), sector)


class ExecutiveScopeTest(unittest.TestCase):
    """Control and judicial own-acts can't evidence the executive's own plan."""

    def test_control_and_judicial_sectors_are_out_of_scope(self):
        # The publishers behind issues #231-#235: appointments, disciplinary
        # rulings and registry annexes, none of which the government executes.
        for sector in ("CONTRALORÍA GENERAL", "PODER JUDICIAL", "MINISTERIO PÚBLICO",
                       "CORTES SUPERIORES DE JUSTICIA", "CONSEJO EJECUTIVO DEL PODER JUDICIAL"):
            self.assertFalse(er.in_national_scope({"sector": sector}), sector)

    def test_statistical_and_electoral_bodies_stay_in_scope(self):
        # INEI publishes the statistics that measure the 65 metas 2031, so it has
        # to stay reachable; its monthly-index noise dies on the phrase gate instead.
        for sector in ("INSTITUTO NACIONAL DE ESTADÍSTICA E INFORMÁTICA",
                       "BANCO CENTRAL DE RESERVA", "JURADO NACIONAL DE ELECCIONES",
                       "REGISTRO NACIONAL DE IDENTIFICACIÓN Y ESTADO CIVIL"):
            self.assertTrue(er.in_national_scope({"sector": sector}), sector)


class NoiseSuppressionTest(unittest.TestCase):
    """Generic bigrams that flooded the queue are suppressed; real signal survives."""

    def setUp(self):
        from tools.scrapers.common import matcher
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
        text = ec.html_to_text(ec.extract_visor_html(page))
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
        self._orig_get, self._orig_sleep = ec.http_get, ec.time.sleep
        ec.time.sleep = lambda *a, **k: None  # no real backoff waits

    def tearDown(self):
        ec.http_get, ec.time.sleep = self._orig_get, self._orig_sleep

    def test_pagination_tail_404_ends_the_edition(self):
        def fake(url):
            if "tipoPublicacion=NL" in url and "start=0" in url:
                return _fake_search_page(ec.PAGE_SIZE, 2000).encode()
            if "tipoPublicacion=NL" in url and "start=20" in url:
                raise _http_error(url, 404)  # past the last NL page
            return _fake_search_page(0).encode()  # BO/PC empty
        ec.http_get = fake
        self.assertEqual(len(ec.fetch_normas("20260101", "2026-01-01")), ec.PAGE_SIZE)

    def test_transient_error_is_retried(self):
        calls = {"n": 0}

        def flaky(url):
            if "tipoPublicacion=NL" in url and "start=0" in url:
                calls["n"] += 1
                if calls["n"] == 1:
                    raise _http_error(url, 404)  # one transient blip
                return _fake_search_page(3, 3000).encode()  # then a short page => NL ends
            return _fake_search_page(0).encode()
        ec.http_get = flaky
        records = ec.fetch_normas("20260101", "2026-01-01")
        self.assertEqual(calls["n"], 2)          # retried once, then succeeded
        self.assertEqual(len(records), 3)

    def test_first_page_404_still_raises(self):
        # a 404 on page 0 is not a pagination tail — it must fail loudly
        ec.http_get = lambda url: (_ for _ in ()).throw(_http_error(url, 404))
        with self.assertRaises(urllib.error.HTTPError):
            ec.fetch_normas("20260101", "2026-01-01")


if __name__ == "__main__":
    unittest.main()


class ExtraordinaryEditionTest(unittest.TestCase):
    """A change of government runs in the Edición Extraordinaria, not Normas Legales.

    Against the real EX search page of 2026-07-28 (page 0 of the day Keiko's
    cabinet was sworn in). NL that day carried five records; EX carried the
    whole cabinet. While TIPOS_PUBLICACION was ("NL", "BO", "PC") the sweep
    read a gazette that had published 19 nombramientos and reported none.
    """

    def setUp(self):
        page = (FIXTURES / "elperuano_search_ex_20260728.html").read_text(encoding="utf-8")
        self.records = ec.parse_search_cards(page, "EX", "2026-07-28")

    def test_the_sweep_reads_the_extraordinary_edition(self):
        self.assertIn("EX", ec.TIPOS_PUBLICACION)

    def test_the_edition_parses_like_any_other(self):
        self.assertEqual(len(self.records), 20)
        for r in self.records:
            self.assertTrue(r["tipo"] and r["numero"] and r["sumilla"])
            self.assertEqual(r["fecha"], "2026-07-28")
            self.assertEqual(r["url"], f"https://busquedas.elperuano.pe/dispositivo/EX/{r['op']}")

    def test_every_card_on_the_page_is_a_cabinet_act(self):
        from tools.scrapers.common.cabinet_rules import is_cabinet_norma
        self.assertTrue(all(is_cabinet_norma(r) for r in self.records))

    def test_carries_the_pcm_appointment(self):
        pcm = next(r for r in self.records
                   if "Presidente del Consejo de Ministros" in r["sumilla"]
                   and r["sumilla"].startswith("Nombran"))
        self.assertEqual(pcm["numero"], "N° 223-2026-PCM")
        self.assertEqual(pcm["tipo"], "RESOLUCIÓN SUPREMA")


class RequestPacingTest(unittest.TestCase):
    """Gazette requests are paced, or the site throttles a sweep into silence."""

    def setUp(self):
        self.real_get, self.real_sleep = ec.http_get, ec.time.sleep
        self.slept = []
        ec.http_get = lambda url, headers=None: b"<html></html>"
        ec.time.sleep = self.slept.append
        ec._last_request = 0.0

    def tearDown(self):
        ec.http_get, ec.time.sleep = self.real_get, self.real_sleep
        ec._last_request = 0.0

    def test_back_to_back_requests_wait(self):
        ec._throttled_get("https://example.test/a")
        self.slept.clear()
        ec._throttled_get("https://example.test/b")
        self.assertTrue(self.slept, "second request went out with no delay")
        self.assertLessEqual(max(self.slept), ec.REQUEST_DELAY)

    def test_norma_text_is_paced_too(self):
        """The /dispositivo/ fetch is one request per norma -- the bulk of a sweep."""
        ec._throttled_get("https://example.test/a")
        self.slept.clear()
        ec.norma_text({"url": "https://example.test/n", "sumilla": "x", "numero": "1"})
        self.assertTrue(self.slept, "norma_text bypassed the pacing")


class NormaTextRetryTest(unittest.TestCase):
    """A norma body gets the same retries a search page does."""

    def setUp(self):
        self.real_get, self.real_sleep = ec.http_get, ec.time.sleep
        ec.time.sleep = lambda _s: None
        ec._last_request = 0.0

    def tearDown(self):
        ec.http_get, ec.time.sleep = self.real_get, self.real_sleep
        ec._last_request = 0.0

    def test_a_transient_failure_does_not_lose_the_body(self):
        calls = []
        body = b'<div id="visor-html"><html><body>Nombran a Fulano de Tal</body></html></div>'

        def flaky(url, headers=None):
            calls.append(url)
            if len(calls) < 3:
                raise urllib.error.URLError("simulated reset")
            return body

        ec.http_get = flaky
        text = ec.norma_text({"url": "https://example.test/n", "sumilla": "Nombran", "numero": "1"})
        self.assertEqual(len(calls), 3)
        self.assertIn("Fulano de Tal", text)

    def test_persistent_failure_still_falls_back_to_the_sumilla(self):
        ec.http_get = lambda url, headers=None: (_ for _ in ()).throw(urllib.error.URLError("down"))
        text = ec.norma_text({"url": "https://example.test/n", "sumilla": "Nombran Ministro", "numero": "1"})
        self.assertEqual(text, "Nombran Ministro")


class InlineTagWordSplitTest(unittest.TestCase):
    """A word broken across styling spans must come back whole.

    Real rendition of R.S. 211-2026-PCM, where the gazette emits
    "…Riego, f</span><span>ormula el señor…". Turning every tag into a space
    gave "f ormula", and _BODY_RESIGN -- which needs that verb -- read the
    norma as unparseable. Two resignations in the 2026-07-28 cabinet edition
    were lost to it.
    """

    def setUp(self):
        self.raw = (FIXTURES / "visor_html_2538522-8.html").read_bytes()

    def test_the_fixture_still_contains_the_split(self):
        """Guards the guard: pointless test if the gazette markup were clean."""
        self.assertIn(b"f</span>", self.raw)

    def test_the_word_survives_extraction(self):
        text = ec.html_to_text(self.raw)
        self.assertNotIn("f ormula", text)
        self.assertIn("formula el señor Felipe César Meza Millán", text)

    def test_block_tags_still_separate_words(self):
        text = ec.html_to_text(b"<p>Ministro de Salud</p><p>Lima, 28 de julio</p>")
        self.assertIn("Salud Lima", text)

    def test_the_resignation_now_parses(self):
        from tools.scrapers.common.cabinet_rules import parse_cabinet_act
        record = {
            "tipo": "RESOLUCIÓN SUPREMA", "numero": "N° 211-2026-PCM",
            "sumilla": "Aceptan renuncia de Ministro de Desarrollo Agrario y Riego",
            "url": "https://busquedas.elperuano.pe/dispositivo/EX/2538522-8",
            "fecha": "2026-07-28", "op": "2538522-8",
        }
        act = parse_cabinet_act(record, ec.html_to_text(self.raw))
        self.assertEqual(act["action"], "renuncia")
        self.assertEqual(act["person"], "Felipe César Meza Millán")
        self.assertEqual(act["portfolio"], "m-agrario")
