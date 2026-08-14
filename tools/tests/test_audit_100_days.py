#!/usr/bin/env python3
"""Tests for the first-100-days archive sweep."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "plan"))
import audit_100_days as audit  # noqa: E402


class ProbeCoverageTest(unittest.TestCase):
    """The probe table is the audit's only defence against a silent blind spot:
    an action with no probe is an action nobody is looking for."""

    def test_every_action_in_the_real_plan_has_a_valid_probe(self):
        actions = audit.load_actions()
        self.assertEqual(len(actions), 67)
        self.assertEqual(audit.check_probe_coverage(actions, audit.load_probes()), [])

    def test_a_missing_probe_is_reported(self):
        actions = [{"id": "t9-9.C01", "text": "x"}, {"id": "t9-9.C02", "text": "y"}]
        problems = audit.check_probe_coverage(actions, {"t9-9.C01": "a"})
        self.assertEqual(problems, ["no probe for t9-9.C02"])

    def test_a_probe_for_a_dropped_action_is_reported(self):
        problems = audit.check_probe_coverage(
            [{"id": "t9-9.C01", "text": "x"}], {"t9-9.C01": "a", "t9-9.C99": "b"})
        self.assertEqual(problems, ["probe for unknown action t9-9.C99"])

    def test_an_invalid_regex_is_reported_not_raised(self):
        problems = audit.check_probe_coverage([{"id": "t9-9.C01", "text": "x"}],
                                              {"t9-9.C01": "([unclosed"})
        self.assertEqual(len(problems), 1)
        self.assertIn("not a valid regex", problems[0])


class GazetteVerifiabilityTest(unittest.TestCase):
    """Splitting the promises by whether a norma could ever prove them is what
    keeps an empty result from reading as proof of inaction."""

    def test_promises_that_require_a_published_norm(self):
        for text in (
            "Publicación del Plan Nacional de Remediación de Pasivos Ambientales",
            "Creación del “Fondo de Emergencia Vial Rural”",
            "Emisión de Decretos de Urgencia para financiar 1,000 patrulleros",
            "Establecimiento de la obligatoriedad del Expediente Judicial Electrónico",
            "Publicación del Reglamento actualizado de Equipaje Inafecto",
        ):
            self.assertTrue(audit._GAZETTE_VERB_RE.search(audit.fold(text)), text)

    def test_promises_that_can_happen_without_any_norm(self):
        for text in (
            "Lanzamiento de la campaña internacional “Vuelve al Perú”",
            "Ejecución de operativos conjuntos MINAM–PNP–SUNAT en puntos críticos",
            "Inicio de operaciones del C5i en Lima y Callao",
            "Reacondicionamiento de 500 canchas y parques deportivos",
            "Despliegue nacional de Brigadas Móviles de Afiliación",
        ):
            self.assertFalse(audit._GAZETTE_VERB_RE.search(audit.fold(text)), text)


class SweepTest(unittest.TestCase):
    def test_a_probe_matches_across_accents_and_case(self):
        actions = [{"id": "t9-9.C01", "text": "x", "topic": "T", "topic_slug": "t",
                    "gazette_can_verify": True}]
        normas = [
            {"fecha": "2026-08-01", "tipo": "DECRETO SUPREMO", "numero": "N° 1",
             "sector": "PCM", "sumilla": "Crean el Fondo Verde Amazónico", "url": "u",
             "_haystack": audit.fold("DECRETO SUPREMO N° 1 Crean el Fondo Verde Amazónico")},
            {"fecha": "2026-08-02", "tipo": "RESOLUCIÓN", "numero": "N° 2",
             "sector": "MEF", "sumilla": "Designan Asesor II", "url": "u",
             "_haystack": audit.fold("RESOLUCIÓN N° 2 Designan Asesor II")},
        ]
        results = audit.sweep(actions, {"t9-9.C01": "fondo verde"}, normas)
        self.assertEqual(len(results[0]["hits"]), 1)
        self.assertEqual(results[0]["hits"][0]["fecha"], "2026-08-01")

    def test_a_promise_nobody_legislated_on_comes_back_empty(self):
        actions = [{"id": "t9-9.C01", "text": "x", "topic": "T", "topic_slug": "t",
                    "gazette_can_verify": False}]
        normas = [{"fecha": "2026-08-01", "tipo": "R", "numero": "1", "sector": "S",
                   "sumilla": "Designan Asesor", "url": "u",
                   "_haystack": "designan asesor"}]
        self.assertEqual(audit.sweep(actions, {"t9-9.C01": "\\bfoniex\\b"}, normas)[0]["hits"], [])


if __name__ == "__main__":
    unittest.main()
