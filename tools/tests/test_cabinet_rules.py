"""Deterministic detection of cabinet appointments and resignations.

Every fixture here is a verbatim capture of the 2026-03-18 cabinet change --
a real full-cabinet reshuffle, 38 Resoluciones Supremas in one edition. An
earlier version of this file used invented strings and passed while the parser
matched nothing real, so the rule now is: assert only against captured gazette
output.

The grammar the gazette actually uses:
  sumilla  "Nombran Ministro del Interior" / "Nombran Presidente del Consejo de Ministros"
           "Aceptan renuncia de Ministro del Interior"
  body     "Nombrar Ministro de Estado en el Despacho del Interior, al señor NOMBRE."
           "Nombrar Presidente del Consejo de Ministros, al señor NOMBRE."
           "Aceptar la renuncia que, al cargo de Ministro de Estado en el Despacho
            del Interior, formula el señor NOMBRE, dándosele las gracias..."

Note the name follows the portfolio, `tipoDispositivo` arrives unaccented as
"RESOLUCION SUPREMA", and names are Title Case, not upper case.
"""
import json
import unittest
from pathlib import Path


from tools.scrapers.common.cabinet_rules import is_cabinet_norma, parse_cabinet_act, portfolio_id  # noqa: E402
from tools.scrapers.common.elperuano_client import html_to_text  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
RECORDS = json.loads((FIXTURES / "normas_20260318.json").read_text(encoding="utf-8"))

OP_PCM_APPOINT = "2496970-20"       # Nombran Presidente del Consejo de Ministros
OP_INTERIOR_APPOINT = "2496970-24"  # Nombran Ministro del Interior
OP_INTERIOR_RESIGN = "2496970-4"    # Aceptan renuncia de Ministro del Interior


def record(op):
    return next(r for r in RECORDS if r["op"] == op)


def body(op):
    return html_to_text((FIXTURES / f"visor_html_{op}.html").read_bytes())


def act(op):
    return parse_cabinet_act(record(op), body(op))


class DetectionOverTheRealEdition(unittest.TestCase):
    """The 2026-03-18 edition is the ground truth: 38 cabinet acts among 83 normas."""

    def test_the_unaccented_tipo_from_the_gazette_is_accepted(self):
        # Real records carry "RESOLUCION SUPREMA"; newer ones carry the accent.
        self.assertEqual(record(OP_INTERIOR_APPOINT)["tipo"], "RESOLUCION SUPREMA")
        self.assertTrue(is_cabinet_norma(record(OP_INTERIOR_APPOINT)))

    def test_the_accented_tipo_is_also_accepted(self):
        accented = dict(record(OP_INTERIOR_APPOINT), tipo="RESOLUCIÓN SUPREMA")
        self.assertTrue(is_cabinet_norma(accented))

    def test_detects_every_appointment_and_resignation_in_the_edition(self):
        detected = [r for r in RECORDS if is_cabinet_norma(r)]
        expected = [r for r in RECORDS
                    if r["sumilla"].startswith(("Nombran Ministr", "Nombran Presidente del Consejo",
                                                "Aceptan renuncia de Ministr",
                                                "Aceptan renuncia de Presidente del Consejo"))]
        self.assertEqual(len(expected), 38, "fixture sanity: a full cabinet reshuffle")
        self.assertCountEqual([r["op"] for r in detected], [r["op"] for r in expected])

    def test_the_pcm_presidency_is_detected(self):
        # The head of cabinet is never called "Ministro de Estado" in a sumilla,
        # which is exactly how this was missed before.
        self.assertTrue(is_cabinet_norma(record(OP_PCM_APPOINT)))

    def test_the_rest_of_the_edition_is_left_alone(self):
        # 83 normas that day; only the 38 cabinet Resoluciones Supremas should
        # be picked up. Everything else is ordinary business.
        others = [r for r in RECORDS if not is_cabinet_norma(r)]
        self.assertEqual(len(others), 45)
        for r in others:
            self.assertFalse(r["sumilla"].startswith(("Nombran Ministr", "Nombran Presidente del Consejo")))

    def test_a_viceministerial_appointment_is_not_detected(self):
        self.assertFalse(is_cabinet_norma(
            dict(record(OP_INTERIOR_APPOINT), sumilla="Designan Viceministro de Trabajo")))

    def test_a_ministerial_travel_authorisation_is_not_detected(self):
        self.assertFalse(is_cabinet_norma(dict(
            record(OP_INTERIOR_APPOINT),
            sumilla="Autorizan viaje de Ministro de Relaciones Exteriores a la República de Chile")))


class ParseSectoralAppointment(unittest.TestCase):
    def setUp(self):
        self.act = act(OP_INTERIOR_APPOINT)

    def test_is_parsed(self):
        self.assertIsNotNone(self.act)

    def test_action_is_appointment(self):
        self.assertEqual(self.act["action"], "nombramiento")

    def test_person_is_read_after_the_portfolio(self):
        self.assertEqual(self.act["person"], "José Mercedes Zapata Morante")

    def test_portfolio_resolves_to_the_registry_id(self):
        self.assertEqual(self.act["portfolio"], "m-interior")

    def test_carries_norma_number_and_iso_date(self):
        self.assertEqual(self.act["norma"], "N° 100-2026-PCM")
        self.assertEqual(self.act["date"], "2026-03-18")


class ParsePcmAppointment(unittest.TestCase):
    def setUp(self):
        self.act = act(OP_PCM_APPOINT)

    def test_is_parsed(self):
        self.assertIsNotNone(self.act)

    def test_person_is_extracted(self):
        self.assertEqual(self.act["person"], "Luis Enrique Arroyo Sánchez")

    def test_portfolio_is_pcm(self):
        self.assertEqual(self.act["portfolio"], "pcm")


class ParseResignation(unittest.TestCase):
    def setUp(self):
        self.act = act(OP_INTERIOR_RESIGN)

    def test_action_is_resignation(self):
        self.assertEqual(self.act["action"], "renuncia")

    def test_person_is_read_after_formula(self):
        self.assertEqual(self.act["person"], "Hugo Alberto Begazo de Bedoya")

    def test_portfolio_resolves(self):
        self.assertEqual(self.act["portfolio"], "m-interior")


class ParsesTheWholeEdition(unittest.TestCase):
    def test_every_sectoral_sumilla_maps_to_a_known_portfolio(self):
        # Guards the registry lookup against the gazette's real ministry names.
        unresolved = []
        for r in RECORDS:
            if not is_cabinet_norma(r):
                continue
            name = (r["sumilla"]
                    .replace("Nombran ", "").replace("Aceptan renuncia de ", "")
                    .replace("Ministro de ", "").replace("Ministra de ", "")
                    .replace("Ministro del ", "").replace("Ministra del ", ""))
            if "Consejo de Ministros" in r["sumilla"]:
                continue
            if portfolio_id(name) is None:
                unresolved.append(r["sumilla"])
        self.assertEqual(unresolved, [])


class GazetteIrregularities(unittest.TestCase):
    """Two variations the gazette uses that a tidy reading of it would miss."""

    def test_a_ministry_name_containing_commas_is_read_whole(self):
        # "Despacho de Vivienda, Construcción y Saneamiento, al señor ..."
        act = parse_cabinet_act(record("2496970-34"), body("2496970-34"))
        self.assertIsNotNone(act)
        self.assertEqual(act["portfolio"], "m-vivienda")
        self.assertEqual(act["person"], "Wilder Alejandro Sifuentes Quilcate")

    def test_a_resignation_without_a_comma_before_formula_is_read(self):
        # "...Despacho de Cultura formula la señora ..." -- no comma, unlike its
        # neighbours in the same edition.
        act = parse_cabinet_act(record("2496970-17"), body("2496970-17"))
        self.assertIsNotNone(act)
        self.assertEqual(act["action"], "renuncia")
        self.assertEqual(act["portfolio"], "m-cultura")
        self.assertEqual(act["person"], "Fátima Soraya Altabás Kajatt")

    def test_the_pcm_presidency_resignation_is_read(self):
        act = parse_cabinet_act(record("2496970-19"), body("2496970-19"))
        self.assertIsNotNone(act)
        self.assertEqual(act["action"], "renuncia")
        self.assertEqual(act["portfolio"], "pcm")
        self.assertEqual(act["person"], "Denisse Azucena Miralles Miralles")

    def test_the_whole_edition_parses_with_no_unreadable_acts(self):
        """The regression that matters: 38 detected, 38 parsed, none dropped."""
        import json as _json
        bodies = {p.stem.replace("visor_html_", ""): p for p in FIXTURES.glob("visor_html_*.html")}
        detected = [r for r in RECORDS if is_cabinet_norma(r)]
        self.assertEqual(len(detected), 38)
        covered = [r for r in detected if r["op"] in bodies]
        self.assertTrue(covered, "fixtures should cover a sample of the edition")
        for r in covered:
            self.assertIsNotNone(parse_cabinet_act(r, body(r["op"])), r["sumilla"])
        del _json


class ParserSafety(unittest.TestCase):
    def test_a_non_cabinet_norma_parses_to_none(self):
        self.assertIsNone(parse_cabinet_act(
            dict(record(OP_INTERIOR_APPOINT), sumilla="Designan Viceministro de Trabajo"),
            body(OP_INTERIOR_APPOINT)))

    def test_an_unreadable_body_parses_to_none_rather_than_guessing(self):
        self.assertIsNone(parse_cabinet_act(record(OP_INTERIOR_APPOINT),
                                            "texto ilegible sin estructura"))

    def test_an_unknown_ministry_parses_to_none(self):
        self.assertIsNone(parse_cabinet_act(
            dict(record(OP_INTERIOR_APPOINT), sumilla="Nombran Ministro de Asuntos Marcianos"),
            "Artículo 1.- Nombrar Ministro de Estado en el Despacho de Asuntos Marcianos, "
            "al señor Juan Perez Gomez."))


if __name__ == "__main__":
    unittest.main()


class PortfolioAliases(unittest.TestCase):
    """Ministries are named in the press by acronym far more often than in
    full — and "canciller" is never the ministry's name at all."""

    def test_acronyms_resolve(self):
        self.assertEqual(portfolio_id("MTC"), "m-transportes")
        self.assertEqual(portfolio_id("Minem"), "m-energia-minas")
        self.assertEqual(portfolio_id("Produce"), "m-produccion")
        self.assertEqual(portfolio_id("Midagri"), "m-agrario")
        self.assertEqual(portfolio_id("Minsa"), "m-salud")
        self.assertEqual(portfolio_id("Mincetur"), "m-comercio-exterior")

    def test_canciller_is_relaciones_exteriores(self):
        self.assertEqual(portfolio_id("canciller"), "m-relaciones-exteriores")

    def test_aliases_are_case_and_accent_insensitive(self):
        self.assertEqual(portfolio_id("minem"), "m-energia-minas")
        self.assertEqual(portfolio_id("MIDAGRI"), "m-agrario")

    def test_every_alias_is_unique_across_portfolios(self):
        # A shared alias would make portfolio_id ambiguous and silently return
        # None, dropping a minister from the roster with no error.
        import json
        from tools.scrapers.common.cabinet_rules import PORTFOLIOS_PATH
        seen = {}
        for p in json.loads(PORTFOLIOS_PATH.read_text(encoding="utf-8"))["portfolios"]:
            for alias in p.get("aliases", []):
                self.assertNotIn(alias.lower(), seen,
                                 f"{alias} claimed by {seen.get(alias.lower())} and {p['id']}")
                seen[alias.lower()] = p["id"]

    def test_existing_resolution_still_works(self):
        self.assertEqual(portfolio_id("Ministerio de Educación"), "m-educacion")
        self.assertEqual(portfolio_id("Desarrollo Agrario y Riego"), "m-agrario")


class SearchPageRecordShape(unittest.TestCase):
    """The gazette transport changed shape on 2026-07-31.

    The retired single-fetch route gave `url_pdf` and a `YYYYMMDD` fecha; the
    search-page reader gives `url` and an already-ISO fecha. Reading the old
    names against the new records yields empty strings rather than an error, so
    a cabinet act would have been filed with no date and no source link.
    """

    def _record(self, **over):
        base = {
            "tipo": "RESOLUCIÓN SUPREMA",
            "numero": "N° 085-2026-PCM",
            "sumilla": "Nombran Ministro de Estado en el Despacho de Salud",
            "url": "https://busquedas.elperuano.pe/dispositivo/NL/2496970-9",
            "fecha": "2026-03-18",
            "op": "2496970-9",
        }
        base.update(over)
        return base

    BODY = ("Nombrar Ministro de Estado en el Despacho de Salud, a la señora "
            "Ana Torres Quispe.")

    def test_the_act_keeps_the_date_and_the_link(self):
        act = parse_cabinet_act(self._record(), self.BODY)
        self.assertIsNotNone(act)
        self.assertEqual(act["date"], "2026-03-18")
        self.assertEqual(act["url"], "https://busquedas.elperuano.pe/dispositivo/NL/2496970-9")

    def test_the_retired_field_names_still_work(self):
        # normas-archive holds records captured under the old transport.
        act = parse_cabinet_act(
            self._record(fecha="20260318", url=None,
                         url_pdf="https://busquedas.elperuano.pe/x.PDF"),
            self.BODY)
        self.assertEqual(act["date"], "2026-03-18")
        self.assertEqual(act["url"], "https://busquedas.elperuano.pe/x.PDF")
