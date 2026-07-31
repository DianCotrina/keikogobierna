"""Matching gazette appointments to the announced roster.

The press names and the gazette names disagree for five of the nineteen
ministers announced on 2026-07-27/28, so this is where a name match has to be
something other than string equality.
"""

import unittest

from tools.scrapers.common.cabinet_rules import reconcile, slugify


def act(portfolio, person, norma="N° 223-2026-PCM", action="nombramiento"):
    return {"action": action, "person": person, "portfolio": portfolio, "norma": norma,
            "date": "2026-07-28",
            "url": f"https://busquedas.elperuano.pe/dispositivo/EX/2538529-1"}


def announced(portfolio, person_name):
    return {"portfolio": portfolio, "person_name": person_name, "announced": "2026-07-27"}


class SlugifyTest(unittest.TestCase):
    def test_folds_accents_and_spaces(self):
        self.assertEqual(slugify("María Magdalena Seminario Marón"),
                         "maria-magdalena-seminario-maron")

    def test_drops_punctuation_without_joining_words(self):
        self.assertEqual(slugify("Alfonso Carlos Espá y Garcés-Alvear"),
                         "alfonso-carlos-espa-y-garces-alvear")


class ReconcileTest(unittest.TestCase):
    def test_builds_a_tenure_and_a_ficha_from_one_norma(self):
        out = reconcile([act("pcm", "Luis Fernando Galarreta Velarde")],
                        [announced("pcm", "Luis Galarreta Velarde")], [])
        self.assertEqual(out["conflicts"], [])
        self.assertEqual(len(out["tenures"]), 1)
        tenure = out["tenures"][0]
        self.assertEqual(tenure["person"], "luis-fernando-galarreta-velarde")
        self.assertEqual(tenure["portfolio"], "pcm")
        self.assertEqual(tenure["start"], "2026-07-28")
        self.assertIsNone(tenure["end"])
        self.assertEqual(tenure["appointment_norma"]["numero"], "N° 223-2026-PCM")

    def test_the_ficha_leaves_what_the_gazette_does_not_say_blank(self):
        out = reconcile([act("pcm", "Luis Fernando Galarreta Velarde")],
                        [announced("pcm", "Luis Galarreta Velarde")], [])
        ficha = out["ministers"][0]
        self.assertEqual(ficha["profession"], "")
        self.assertEqual(ficha["bio"], "")
        self.assertEqual(ficha["judicial"], [])
        self.assertEqual(ficha["sources"][0]["kind"], "primary")
        self.assertIn("223-2026-PCM", ficha["sources"][0]["label"])

    def test_a_press_name_missing_middle_names_still_matches(self):
        """Real: the press printed "Mara Seminario Marón" for María Magdalena."""
        out = reconcile([act("m-mujer", "María Magdalena Seminario Marón")],
                        [announced("m-mujer", "Mara Seminario Marón")], [])
        self.assertEqual(out["conflicts"], [])
        self.assertEqual(out["tenures"][0]["person"], "maria-magdalena-seminario-maron")

    def test_a_press_name_with_a_wrong_given_name_still_matches(self):
        """Real: "Roger Valencia Espinoza" in the press, "Rogers Martín" in the norma."""
        out = reconcile([act("m-comercio-exterior", "Rogers Martín Valencia Espinoza")],
                        [announced("m-comercio-exterior", "Roger Valencia Espinoza")], [])
        self.assertEqual(out["conflicts"], [])

    def test_a_different_person_is_flagged_not_merged(self):
        out = reconcile([act("m-salud", "Luis Williams Dyer Fernández")],
                        [announced("m-salud", "Carmen Rivas Ponce")], [])
        self.assertEqual([c["kind"] for c in out["conflicts"]], ["nombre-distinto"])
        self.assertEqual(out["conflicts"][0]["announced"], "Carmen Rivas Ponce")
        # Still proposed -- the gazette outranks the press; a person decides.
        self.assertEqual(len(out["tenures"]), 1)

    def test_an_announcement_with_no_norma_is_reported(self):
        out = reconcile([], [announced("m-salud", "Luis Dyer Fernández")], [])
        self.assertEqual([c["kind"] for c in out["conflicts"]], ["sin-norma"])
        self.assertEqual(out["tenures"], [])

    def test_a_norma_nobody_announced_is_reported(self):
        out = reconcile([act("m-salud", "Luis Williams Dyer Fernández")], [], [])
        self.assertEqual([c["kind"] for c in out["conflicts"]], ["sin-anuncio"])

    def test_an_existing_ficha_is_not_duplicated(self):
        out = reconcile([act("pcm", "Luis Fernando Galarreta Velarde")],
                        [announced("pcm", "Luis Galarreta Velarde")],
                        [{"slug": "luis-fernando-galarreta-velarde", "name": "x"}])
        self.assertEqual(out["ministers"], [])
        self.assertEqual(len(out["tenures"]), 1)  # the tenure is still needed

    def test_resignations_are_not_turned_into_tenures(self):
        out = reconcile([act("m-salud", "Juan Carlos Velasco Guerrero", action="renuncia")],
                        [], [])
        self.assertEqual(out["tenures"], [])
        self.assertEqual(out["ministers"], [])


if __name__ == "__main__":
    unittest.main()
