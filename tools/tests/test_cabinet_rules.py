"""Deterministic detection of cabinet appointments and resignations.

Appointment normas are highly formulaic, which is what makes regex the right
tool and keeps the no-AI-in-pipelines invariant intact. The strings below follow
the gazette's own grammar; the parser must never guess.

Note: these are structural strings, not a captured ministerial appointment --
the 2026 cabinet is sworn in on 2026-07-28 and no such norma exists yet. Re-run
against real gazette output before any roster data is committed.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scrapers"))

from cabinet_rules import is_cabinet_norma, parse_cabinet_act  # noqa: E402


def norma(sumilla, tipo="RESOLUCIÓN SUPREMA", sector="PRESIDENCIA DEL CONSEJO DE MINISTROS"):
    return {"tipo": tipo, "numero": "N° 001-2026-PCM", "sector": sector,
            "rubro": "NL", "sumilla": sumilla, "fecha": "20260728",
            "op": "2538239-1", "url_pdf": "https://busquedas.elperuano.pe/x.PDF"}


APPOINT = norma("Nombran Ministro de Estado en el Despacho del Interior")
APPOINT_BODY = (
    "RESOLUCIÓN SUPREMA N° 001-2026-PCM\n"
    "EL PRESIDENTE DE LA REPÚBLICA\n"
    "SE RESUELVE:\n"
    "Artículo 1.- Nombrar al señor JUAN CARLOS PEREZ GARCIA como Ministro de "
    "Estado en el Despacho del Interior.\n"
    "Regístrese, comuníquese y publíquese."
)


class Detection(unittest.TestCase):
    def test_an_appointment_is_a_cabinet_norma(self):
        self.assertTrue(is_cabinet_norma(APPOINT))

    def test_a_resignation_is_a_cabinet_norma(self):
        self.assertTrue(is_cabinet_norma(
            norma("Aceptan renuncia de Ministra de Estado en el Despacho de Salud")))

    def test_a_viceministerial_appointment_is_not_a_cabinet_norma(self):
        # The single most likely false positive: viceministers are appointed
        # constantly and are not cabinet members.
        self.assertFalse(is_cabinet_norma(norma("Designan Viceministro de Trabajo")))
        self.assertFalse(is_cabinet_norma(
            norma("Designan Viceministra de Estado en el Despacho de Educación")))

    def test_an_unrelated_norma_is_not_a_cabinet_norma(self):
        self.assertFalse(is_cabinet_norma(
            norma("Autorizan viaje de docentes en comisión de servicios")))

    def test_a_resolucion_ministerial_is_not_a_cabinet_norma(self):
        # Ministers are appointed by Resolución Suprema only.
        self.assertFalse(is_cabinet_norma(
            norma("Nombran Ministro de Estado en el Despacho del Interior",
                  tipo="RESOLUCIÓN MINISTERIAL")))


class ParseAppointment(unittest.TestCase):
    def setUp(self):
        self.act = parse_cabinet_act(APPOINT, APPOINT_BODY)

    def test_returns_an_appointment(self):
        self.assertEqual(self.act["action"], "nombramiento")

    def test_extracts_the_person_from_the_body(self):
        self.assertEqual(self.act["person"], "JUAN CARLOS PEREZ GARCIA")

    def test_maps_the_portfolio_to_a_registry_id(self):
        self.assertEqual(self.act["portfolio"], "m-interior")

    def test_carries_the_certifying_norma_and_an_iso_date(self):
        self.assertEqual(self.act["norma"], "N° 001-2026-PCM")
        self.assertEqual(self.act["date"], "2026-07-28")
        self.assertTrue(self.act["url"].startswith("https://"))

    def test_handles_a_female_minister(self):
        act = parse_cabinet_act(
            norma("Nombran Ministra de Estado en el Despacho de Salud"),
            "Artículo 1.- Nombrar a la señora MARIA LOPEZ DIAZ como Ministra de "
            "Estado en el Despacho de Salud.")
        self.assertEqual(act["person"], "MARIA LOPEZ DIAZ")
        self.assertEqual(act["portfolio"], "m-salud")

    def test_maps_a_multiword_portfolio(self):
        act = parse_cabinet_act(
            norma("Nombran Ministro de Estado en el Despacho de Economía y Finanzas"),
            "Artículo 1.- Nombrar al señor LUIS RAMOS SOTO como Ministro de Estado "
            "en el Despacho de Economía y Finanzas.")
        self.assertEqual(act["portfolio"], "m-economia")


class ParseResignation(unittest.TestCase):
    def test_returns_a_resignation(self):
        act = parse_cabinet_act(
            norma("Aceptan renuncia de Ministro de Estado en el Despacho de Cultura"),
            "Artículo 1.- Aceptar la renuncia del señor PEDRO SILVA MORA al cargo de "
            "Ministro de Estado en el Despacho de Cultura.")
        self.assertEqual(act["action"], "renuncia")
        self.assertEqual(act["person"], "PEDRO SILVA MORA")
        self.assertEqual(act["portfolio"], "m-cultura")


class ParserSafety(unittest.TestCase):
    def test_a_non_cabinet_norma_parses_to_none(self):
        self.assertIsNone(parse_cabinet_act(
            norma("Designan Viceministro de Trabajo"), "Artículo 1.- Designar..."))

    def test_an_unreadable_body_parses_to_none_rather_than_guessing(self):
        self.assertIsNone(parse_cabinet_act(APPOINT, "texto ilegible sin estructura"))

    def test_an_unknown_portfolio_parses_to_none(self):
        # Better to file nothing than to invent a ministry that is not in the registry.
        self.assertIsNone(parse_cabinet_act(
            norma("Nombran Ministro de Estado en el Despacho de Asuntos Marcianos"),
            "Artículo 1.- Nombrar al señor X Y Z como Ministro de Estado en el "
            "Despacho de Asuntos Marcianos."))


if __name__ == "__main__":
    unittest.main()
