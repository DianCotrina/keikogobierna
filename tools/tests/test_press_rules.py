"""Cabinet announcements read from press headlines.

A proclamation is not a Resolución Suprema, so what this produces is always
provisional — it feeds the "anunciado" state and is superseded the moment the
gazette publishes. See tools/scrapers/common/press_rules.py.

Fixtures are verbatim captures of the El Comercio and La República politics
feeds from 2026-07-27, the day the cabinet was presented. They carry both the
real announcements and the headlines that must NOT be mistaken for one.
"""
import unittest
from pathlib import Path


from tools.scrapers.common.press_rules import parse_announcement, announcements_from  # noqa: E402
from tools.scrapers.ultimitas_scraper import parse_feed  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def feed(name, source):
    return parse_feed((FIXTURES / name).read_bytes(), source)


ITEMS = (feed("elcomercio_politica_20260727.xml", "El Comercio")
         + feed("larepublica_politica_20260727.xml", "La República"))


def item(title, source="El Comercio", url="https://elcomercio.pe/x", published="2026-07-27T12:00:00Z"):
    # Same field names ultimitas_scraper.parse_feed produces.
    return {"title": title, "source": source, "url": url, "published": published}


class RealAnnouncements(unittest.TestCase):
    def test_the_pcm_announcement_is_read(self):
        act = parse_announcement(item(
            "Keiko Fujimori presenta a Luis Galarreta como próximo presidente del Consejo de Ministros"))
        self.assertIsNotNone(act)
        self.assertEqual(act["person_name"], "Luis Galarreta")
        self.assertEqual(act["portfolio"], "pcm")

    def test_a_sectoral_announcement_is_read(self):
        act = parse_announcement(item(
            "Keiko Fujimori presenta a Carlos Espá como próximo ministro de Relaciones Exteriores"))
        self.assertIsNotNone(act)
        self.assertEqual(act["person_name"], "Carlos Espá")
        self.assertEqual(act["portfolio"], "m-relaciones-exteriores")

    def test_the_anuncia_que_phrasing_is_read(self):
        act = parse_announcement(item(
            "Keiko Fujimori anuncia que Luis Galarreta será el presidente del Consejo de Ministros",
            source="La República"))
        self.assertIsNotNone(act)
        self.assertEqual(act["person_name"], "Luis Galarreta")
        self.assertEqual(act["portfolio"], "pcm")

    def test_the_announcement_carries_its_press_source(self):
        act = parse_announcement(item(
            "Keiko Fujimori presenta a Carlos Espá como próximo ministro de Relaciones Exteriores"))
        self.assertEqual(act["sources"][0]["kind"], "press")
        self.assertEqual(act["sources"][0]["label"], "El Comercio")
        self.assertTrue(act["sources"][0]["url"].startswith("https://"))
        self.assertEqual(act["announced"], "2026-07-27")


class HeadlinesWithTrailingQualifiers(unittest.TestCase):
    """Headlines rarely end at the ministry name.

    "...como ministro de Economía de su primer gabinete" must resolve to
    m-economia; an office capture that swallows the trailing clause resolves to
    nothing and the announcement is silently lost.
    """

    def test_a_trailing_clause_after_the_ministry_is_ignored(self):
        act = parse_announcement(item(
            "Keiko Fujimori anuncia a Elmer Cuba como ministro de Economía de su primer gabinete"))
        self.assertIsNotNone(act)
        self.assertEqual(act["person_name"], "Elmer Cuba")
        self.assertEqual(act["portfolio"], "m-economia")

    def test_the_colloquial_short_ministry_name_resolves(self):
        # The press says "ministro de Economía"; the registry says
        # "Ministerio de Economía y Finanzas".
        act = parse_announcement(item(
            "Keiko Fujimori anuncia a Elmer Cuba como ministro de Economía"))
        self.assertEqual(act["portfolio"], "m-economia")

    def test_another_trailing_clause_shape(self):
        act = parse_announcement(item(
            "Keiko Fujimori presenta a Juan Perez como ministro de Salud del nuevo gobierno"))
        self.assertIsNotNone(act)
        self.assertEqual(act["portfolio"], "m-salud")

    def test_past_tense_reporting_is_read(self):
        # Ledes commonly use the preterite: "anunció a X como ...".
        act = parse_announcement(item(
            "Keiko Fujimori anunció a Elmer Cuba como nuevo ministro de Economía y Finanzas"))
        self.assertIsNotNone(act)
        self.assertEqual(act["person_name"], "Elmer Cuba")
        self.assertEqual(act["portfolio"], "m-economia")

    def test_an_ambiguous_prefix_still_resolves_to_nothing(self):
        # "Desarrollo" alone matches both Desarrollo Agrario and Desarrollo e
        # Inclusión Social, so it must stay unresolved rather than pick one.
        self.assertIsNone(parse_announcement(item(
            "Keiko Fujimori presenta a Juan Perez como ministro de Desarrollo")))


class NotAnnouncements(unittest.TestCase):
    """Every one of these appeared in the same feeds on the same day."""

    def test_an_exminister_quote_is_not_an_announcement(self):
        self.assertIsNone(parse_announcement(item(
            "Waldo Mendoza, exministro de Economía: “Un fenómeno de El Niño no tiene por qué provocar recesión”")))

    def test_football_is_not_an_announcement(self):
        self.assertIsNone(parse_announcement(item(
            "La Premier League alista una revolucionaria regla para evitar que arqueros hagan tiempo")))

    def test_commentary_about_choosing_a_premier_is_not_an_announcement(self):
        self.assertIsNone(parse_announcement(item(
            "Alfonso López Chau: “La presidenta Keiko Fujimori puede elegir legítimamente quién va a ser su premier”")))

    def test_a_profile_piece_is_not_an_announcement(self):
        # Names the right person and office, but announces nothing.
        self.assertIsNone(parse_announcement(item(
            "¿Quién es Luis Galarreta, el nuevo presidente del Consejo de Ministros de Keiko Fujimori?")))

    def test_a_background_piece_is_not_an_announcement(self):
        self.assertIsNone(parse_announcement(item(
            "Luis Galarreta, del círculo de confianza de Keiko Fujimori y Fuerza Popular a próximo "
            "presidente del Consejo de Ministros")))

    def test_an_unknown_ministry_is_not_announced(self):
        self.assertIsNone(parse_announcement(item(
            "Keiko Fujimori presenta a Juan Perez como próximo ministro de Asuntos Marcianos")))


class OverTheRealFeeds(unittest.TestCase):
    def test_exactly_the_two_announced_ministers_are_found(self):
        found = announcements_from(ITEMS)
        self.assertEqual({(a["person_name"], a["portfolio"]) for a in found},
                         {("Luis Galarreta", "pcm"), ("Carlos Espá", "m-relaciones-exteriores")})

    def test_duplicate_coverage_is_collapsed_but_sources_accumulate(self):
        # Two outlets reported Galarreta; that is one announcement with two sources.
        found = announcements_from(ITEMS)
        pcm = next(a for a in found if a["portfolio"] == "pcm")
        self.assertGreaterEqual(len(pcm["sources"]), 2)
        labels = {s["label"] for s in pcm["sources"]}
        self.assertIn("El Comercio", labels)
        self.assertIn("La República", labels)

    def test_no_other_headline_in_the_capture_is_treated_as_an_announcement(self):
        self.assertEqual(len(announcements_from(ITEMS)), 2)


if __name__ == "__main__":
    unittest.main()
