"""Judicial signals mined from press coverage of people on the cabinet roster.

Press reports allegations far more loosely than a court records them, so this
produces discovery only: a GitHub issue for a human to check against a primary
source. It never writes cabinet data and never assigns a stage.

The rule is scoped to the roster on purpose. These all ran in the live feeds on
2026-07-27 and are judicial-shaped, yet none concerns a Peruvian minister:

    "Putin acusa a Occidente de recurrir a métodos terroristas"
    "Javier Milei acusa a Brasil y México de financiar campaña antiargentina"
    "Millonaria estafa postal: dos hombres acusados de vender estampillas falsas"

A general accusation detector would surface all three. Requiring a roster name
makes the rule both precise and relevant.
"""
import unittest
from pathlib import Path


from tools.scrapers.common.press_rules import judicial_signals  # noqa: E402

ROSTER = ["Roberto Sánchez", "Delia Espinoza", "Luis Galarreta"]


def item(title, source="El Comercio", url="https://elcomercio.pe/x",
         published="2026-07-27T12:00:00Z", summary=""):
    return {"title": title, "source": source, "url": url,
            "published": published, "summary": summary}


class FiresOnRosterPeople(unittest.TestCase):
    def test_a_real_court_setback_is_flagged(self):
        signals = judicial_signals([item(
            "Nuevo revés para Roberto Sánchez: PJ rechaza su intento de anular "
            "juicio oral en caso aportes ONPE")], ROSTER)
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0]["person_name"], "Roberto Sánchez")

    def test_an_archived_investigation_is_flagged_too(self):
        # Exculpatory news matters as much as accusatory news.
        signals = judicial_signals([item(
            "Delia Espinoza: Poder Judicial archiva definitivamente investigación "
            "por abuso de autoridad")], ROSTER)
        self.assertEqual(len(signals), 1)
        self.assertIn("archiva", signals[0]["matched"].lower())

    def test_the_signal_never_carries_a_stage(self):
        signals = judicial_signals([item(
            "Poder Judicial condena a Roberto Sánchez")], ROSTER)
        self.assertNotIn("stage", signals[0])

    def test_the_signal_carries_its_article(self):
        signals = judicial_signals([item(
            "Fiscalía abre investigación preliminar contra Luis Galarreta")], ROSTER)
        s = signals[0]
        self.assertTrue(s["url"].startswith("https://"))
        self.assertEqual(s["source"], "El Comercio")
        self.assertEqual(s["published"], "2026-07-27")

    def test_the_summary_is_read_as_well_as_the_title(self):
        signals = judicial_signals([item(
            "Cambios en el gabinete",
            summary="La fiscalía abrió una investigación contra Luis Galarreta.")], ROSTER)
        self.assertEqual(len(signals), 1)


class IgnoresEveryoneElse(unittest.TestCase):
    """Real headlines from the same feeds that must not produce a signal."""

    def test_a_foreign_leader_is_ignored(self):
        self.assertEqual(judicial_signals([item(
            "Putin acusa a Occidente de recurrir a “métodos terroristas”")], ROSTER), [])

    def test_another_foreign_leader_is_ignored(self):
        self.assertEqual(judicial_signals([item(
            "Javier Milei acusa a Brasil y México de financiar “campaña antiargentina”")],
            ROSTER), [])

    def test_unrelated_crime_news_is_ignored(self):
        self.assertEqual(judicial_signals([item(
            "Millonaria estafa postal: dos hombres acusados de vender estampillas falsas")],
            ROSTER), [])

    def test_institutional_news_without_an_accused_person_is_ignored(self):
        self.assertEqual(judicial_signals([item(
            "Ministerio Público: reorganizan fiscalías de lavado de activos")], ROSTER), [])

    def test_a_roster_name_without_judicial_language_is_ignored(self):
        self.assertEqual(judicial_signals([item(
            "Luis Galarreta lidera la PCM y presenta a su equipo")], ROSTER), [])

    def test_an_empty_roster_produces_nothing(self):
        self.assertEqual(judicial_signals([item(
            "Poder Judicial condena a Roberto Sánchez")], []), [])


class Deduplication(unittest.TestCase):
    def test_the_same_article_twice_yields_one_signal(self):
        article = item("Poder Judicial condena a Roberto Sánchez")
        self.assertEqual(len(judicial_signals([article, dict(article)], ROSTER)), 1)

    def test_two_articles_about_one_person_both_surface(self):
        signals = judicial_signals([
            item("Poder Judicial condena a Roberto Sánchez", url="https://a.pe/1"),
            item("Fiscalía acusa a Roberto Sánchez", url="https://a.pe/2"),
        ], ROSTER)
        self.assertEqual(len(signals), 2)


if __name__ == "__main__":
    unittest.main()
