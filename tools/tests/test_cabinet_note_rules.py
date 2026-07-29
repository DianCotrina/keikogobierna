"""Reading a cabinet from El Peruano's own news note.

The gazette lags: a cabinet is sworn in hours before the Resoluciones Supremas
that appoint it are published. El Peruano's news desk publishes the full roster
the same evening, in a structured list, which is a far better source than
chasing nineteen separate press headlines.

Fixture is the real page, captured 2026-07-28.
"""
import unittest
from pathlib import Path


from tools.scrapers.common.cabinet_note_rules import parse_cabinet_note  # noqa: E402

FIXTURE = Path(__file__).parent / "fixtures" / "elperuano_noticia_301303.html"
HTML = FIXTURE.read_text(encoding="utf-8", errors="replace")
ENTRIES = parse_cabinet_note(HTML)
BY_PORTFOLIO = {e["portfolio"]: e for e in ENTRIES}


class TheWholeCabinet(unittest.TestCase):
    def test_every_portfolio_is_read(self):
        # The site tracks 19 carteras and this note names all 19.
        self.assertEqual(len(ENTRIES), 19, [e["portfolio"] for e in ENTRIES])

    def test_every_entry_resolves_to_a_known_portfolio(self):
        # A portfolio the registry does not know would be dropped silently
        # otherwise, and the roster would quietly under-report.
        self.assertEqual([e for e in ENTRIES if not e["portfolio"]], [])

    def test_no_portfolio_is_claimed_twice(self):
        self.assertEqual(len(BY_PORTFOLIO), len(ENTRIES))

    def test_the_premier_is_read_from_a_different_title(self):
        # "Presidente del Consejo de Ministros" never says the word "Ministro de".
        self.assertEqual(BY_PORTFOLIO["pcm"]["person_name"], "Luis Galarreta Velarde")


class NamesAreClean(unittest.TestCase):
    def test_full_names_survive(self):
        self.assertEqual(BY_PORTFOLIO["m-economia"]["person_name"], "Elmer Cuba Bustinza")
        self.assertEqual(BY_PORTFOLIO["m-defensa"]["person_name"], "Rafael Belaunde Llosa")

    def test_a_name_containing_y_is_not_truncated(self):
        # "Carlos Espá y Garcés-Alvear" — the conjunction and the hyphen both
        # sit inside the surname, and this is the name that finally identifies
        # him against the Fuerza Popular homonym problem.
        self.assertEqual(
            BY_PORTFOLIO["m-relaciones-exteriores"]["person_name"],
            "Carlos Espá y Garcés-Alvear",
        )

    def test_accents_and_enye_survive(self):
        self.assertEqual(BY_PORTFOLIO["m-interior"]["person_name"], "César Astudillo Salcedo")
        self.assertEqual(BY_PORTFOLIO["m-energia-minas"]["person_name"], "Guillermo Shinno Huamaní")

    def test_a_female_title_is_read(self):
        # "Ministra de la Mujer y Poblaciones Vulnerables".
        self.assertEqual(BY_PORTFOLIO["m-mujer"]["person_name"], "Mara Seminario Marón")

    def test_no_name_carries_a_trailing_role_word(self):
        for entry in ENTRIES:
            self.assertNotRegex(entry["person_name"], r"(?i)ministr[oa]|presidente")
            self.assertLess(len(entry["person_name"]), 60, entry)

    def test_the_last_name_does_not_run_into_the_prose_that_follows(self):
        # Reading the page as one flat string made the final entry come out as
        # "Juan Carlos Requejo Alemán Lea", swallowing the "Lea también en El
        # Peruano" heading underneath it. The block boundary is what stops it.
        self.assertEqual(
            BY_PORTFOLIO["m-produccion"]["person_name"],
            "Juan Carlos Requejo Alemán",
        )


class RejectsWhatIsNotACabinetNote(unittest.TestCase):
    def test_an_unrelated_page_yields_nothing(self):
        self.assertEqual(parse_cabinet_note("<p>Keiko Fujimori juró como presidenta.</p>"), [])

    def test_empty_input_yields_nothing(self):
        self.assertEqual(parse_cabinet_note(""), [])
        self.assertEqual(parse_cabinet_note(None), [])


if __name__ == "__main__":
    unittest.main()
