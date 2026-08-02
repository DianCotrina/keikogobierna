"""The per-minister coverage index written for the dossier pages."""

import unittest
from datetime import datetime, timezone

from tools.scrapers.common import minister_news as mn

ROSTER = [
    {"portfolio": "m-economia", "person_name": "Elmer Rafael Cuba Bustinza",
     "slug": "elmer-rafael-cuba-bustinza"},
    {"portfolio": "m-trabajo", "person_name": "Juan Manuel Kosme Sheput Moore",
     "slug": "juan-manuel-kosme-sheput-moore"},
]
NOW = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)


def article(title, published, url="https://gestion.pe/n/", source="Gestión", summary=""):
    return {"title": title, "summary": summary, "url": url,
            "source": source, "published": published, "author": "Redacción"}


class WindowTest(unittest.TestCase):
    def test_an_article_from_six_days_ago_is_kept(self):
        a = article("El ministro de Economía Cuba anuncia medidas", "2026-07-26T10:00:00-05:00")
        index = mn.build_index([a], ROSTER, NOW)
        self.assertIn("elmer-rafael-cuba-bustinza", index)

    def test_an_article_from_eight_days_ago_is_dropped(self):
        a = article("El ministro de Economía Cuba anuncia medidas", "2026-07-24T10:00:00-05:00")
        self.assertEqual(mn.build_index([a], ROSTER, NOW), {})

    def test_an_unparseable_date_is_dropped_rather_than_kept_forever(self):
        a = article("El ministro de Economía Cuba anuncia medidas", "no es una fecha")
        self.assertEqual(mn.build_index([a], ROSTER, NOW), {})

    def test_a_naive_date_is_dropped_rather_than_kept_forever(self):
        a = article("El ministro de Economía Cuba anuncia medidas", "2026-08-01T09:00:00")
        self.assertEqual(mn.build_index([a], ROSTER, NOW), {})


class ShapeTest(unittest.TestCase):
    def setUp(self):
        self.index = mn.build_index(
            [article("El ministro de Economía Cuba anuncia medidas", "2026-08-01T09:00:00-05:00",
                     summary="Un resumen que no debe publicarse.")],
            ROSTER, NOW)

    def test_keyed_by_slug_not_cartera(self):
        self.assertEqual(list(self.index), ["elmer-rafael-cuba-bustinza"])

    def test_carries_only_the_published_fields(self):
        entry = self.index["elmer-rafael-cuba-bustinza"][0]
        self.assertEqual(set(entry), {"title", "url", "source", "published", "matched_in"})

    def test_the_feed_summary_is_not_shipped(self):
        entry = self.index["elmer-rafael-cuba-bustinza"][0]
        self.assertNotIn("summary", entry)


class OrderTest(unittest.TestCase):
    def test_newest_first(self):
        articles = [
            article("El ministro de Economía Cuba, lunes", "2026-07-27T10:00:00-05:00", url="https://a/"),
            article("El ministro de Economía Cuba, viernes", "2026-07-31T10:00:00-05:00", url="https://b/"),
        ]
        index = mn.build_index(articles, ROSTER, NOW)
        self.assertEqual([e["url"] for e in index["elmer-rafael-cuba-bustinza"]],
                         ["https://b/", "https://a/"])

    def test_newest_first_across_offsets(self):
        """RPP publishes at Lima time (-05:00), La República at GMT (+00:00).

        05:09 at -05:00 is 10:09 UTC — genuinely newer than 05:33 at +00:00 —
        but "2026-07-31T05:09:45-05:00" sorts *before*
        "2026-07-31T05:33:12+00:00" as a raw string. A sort on the string
        would put the older article first; the parsed instant must not.
        """
        articles = [
            article("El ministro de Economía Cuba en RPP", "2026-07-31T05:09:45-05:00",
                     url="https://rpp/", source="RPP"),
            article("El ministro de Economía Cuba en La República", "2026-07-31T05:33:12+00:00",
                     url="https://larepublica/", source="La República"),
        ]
        index = mn.build_index(articles, ROSTER, NOW)
        self.assertEqual([e["url"] for e in index["elmer-rafael-cuba-bustinza"]],
                         ["https://rpp/", "https://larepublica/"])


class CoverageTest(unittest.TestCase):
    def test_a_minister_with_no_coverage_is_absent(self):
        a = article("El ministro de Economía Cuba anuncia medidas", "2026-08-01T09:00:00-05:00")
        self.assertNotIn("juan-manuel-kosme-sheput-moore", mn.build_index([a], ROSTER, NOW))

    def test_an_article_naming_two_ministers_lands_under_both(self):
        a = article("El ministro de Economía Cuba y el ministro de Trabajo Sheput coordinan",
                    "2026-08-01T09:00:00-05:00")
        index = mn.build_index([a], ROSTER, NOW)
        self.assertEqual(set(index), {"elmer-rafael-cuba-bustinza", "juan-manuel-kosme-sheput-moore"})

    def test_a_roster_row_without_a_slug_is_skipped(self):
        """An announced cartera has no ficha and therefore no page to link to."""
        roster = [{"portfolio": "m-economia", "person_name": "Elmer Rafael Cuba Bustinza"}]
        a = article("El ministro de Economía Cuba anuncia medidas", "2026-08-01T09:00:00-05:00")
        self.assertEqual(mn.build_index([a], roster, NOW), {})


class MatchedInTest(unittest.TestCase):
    """Presence must not read as aboutness: a match on the feed summary alone
    still counts as coverage, but the dossier needs to tell the two cases
    apart. `matched_in` records whether the *headline* gives a reader any
    reason to connect it to this minister — apellido OR cartera, either is
    enough, not the two-key AND `names_minister` uses for matching itself.
    Requiring both in the headline was tried and rejected twice: apellido-only
    still missed headlines naming the office and not the person ("Ministro de
    Cultura: 'No voy a cerrar el LUM'"), and against live data the full
    two-key rule misclassified headlines naming either as summary-only at 16
    of 18 cards on one dossier — a flag that fires almost always stops
    meaning anything, and the case it exists for (a headline connecting to
    neither) stops standing out."""

    ROSTER = [
        {"portfolio": "m-economia", "person_name": "Elmer Rafael Cuba Bustinza",
         "slug": "elmer-rafael-cuba-bustinza"},
        {"portfolio": "m-relaciones-exteriores", "person_name": "Carlos Espá y Garcés-Alvear",
         "slug": "alfonso-carlos-espa-y-garces-alvear"},
        {"portfolio": "m-agrario", "person_name": "Marco Vinelli Ruiz",
         "slug": "marco-vinelli-ruiz"},
        {"portfolio": "m-cultura", "person_name": "Alberto Ismael Beingolea Delgado",
         "slug": "alberto-ismael-beingolea-delgado"},
        {"portfolio": "m-educacion", "person_name": "José Antonio Chang Escobedo",
         "slug": "jose-antonio-chang-escobedo"},
    ]

    def test_a_headline_naming_both_apellido_and_cartera_is_title(self):
        a = article("El ministro de Economía Cuba anuncia medidas", "2026-08-01T09:00:00-05:00")
        index = mn.build_index([a], self.ROSTER, NOW)
        self.assertEqual(index["elmer-rafael-cuba-bustinza"][0]["matched_in"], "title")

    def test_a_headline_naming_the_apellido_without_the_cartera_is_title(self):
        """A real headline that leads with the minister's own surname but
        never spells out "Cultura" or "ministro de ..." — the cartera comes
        from the summary, the headline alone still plainly names him."""
        a = article(
            'Beingolea señala que pedido de facultades legislativas aún "se afina" '
            'y descarta cierre del LUM',
            "2026-08-02T09:00:00-05:00",
            summary=("El ministro de Cultura, Alberto Beingolea, se pronunció sobre "
                      "el pedido de facultades legislativas del Ejecutivo."),
        )
        index = mn.build_index([a], self.ROSTER, NOW)
        self.assertEqual(
            index["alberto-ismael-beingolea-delgado"][0]["matched_in"], "title")

    def test_a_headline_naming_the_cartera_without_the_apellido_is_title(self):
        """A real headline that names the office, not the officeholder —
        the dossier belongs to whoever holds Cultura right now, so a headline
        about "el ministro de Cultura" names him even without "Beingolea"."""
        a = article('Ministro de Cultura: "No voy a cerrar el LUM"',
                     "2026-08-02T09:00:00-05:00",
                     summary="Alberto Beingolea descartó el cierre del Lugar de la Memoria.")
        index = mn.build_index([a], self.ROSTER, NOW)
        self.assertEqual(
            index["alberto-ismael-beingolea-delgado"][0]["matched_in"], "title")

    def test_a_cartera_acronym_in_the_headline_without_the_apellido_is_title(self):
        """The registry's acronyms count too, same as the full name would —
        `_carteras_named` already resolves "Minedu", this only has to reuse
        it."""
        a = article("Minedu envía los primeros 20 domos a Chupaca para reanudar clases",
                     "2026-08-02T09:00:00-05:00",
                     summary="El ministro de Educación, José Chang, supervisó el envío.")
        index = mn.build_index([a], self.ROSTER, NOW)
        self.assertEqual(
            index["jose-antonio-chang-escobedo"][0]["matched_in"], "title")

    def test_a_headline_naming_neither_is_summary(self):
        a = article("Anuncios del gabinete", "2026-08-01T09:00:00-05:00",
                    summary="El ministro de Economía Cuba presentó el paquete.")
        index = mn.build_index([a], self.ROSTER, NOW)
        self.assertEqual(index["elmer-rafael-cuba-bustinza"][0]["matched_in"], "summary")

    def test_the_espa_case_matches_on_summary_only(self):
        """The real live-feed case that motivated this change: the headline
        names a different minister entirely (Marco Vinelli, on Betssy
        Chávez), and only the feed summary names Espá."""
        a = article(
            'Marco Vinelli considera que el Ejecutivo otorgará salvoconducto a '
            'Betssy Chávez: "Yo creo que sí"',
            "2026-08-01T09:00:00-05:00",
            summary=("Antes de ello, Carlos Espá, ministro de Relaciones Exteriores, "
                      "había deslizado la posibilidad de un salvoconducto."),
        )
        index = mn.build_index([a], self.ROSTER, NOW)
        self.assertEqual(
            index["alfonso-carlos-espa-y-garces-alvear"][0]["matched_in"], "summary")
        # And Vinelli himself is not matched at all: his name appears, but
        # neither his cartera nor his surname's own ministry phrase does.
        self.assertNotIn("marco-vinelli-ruiz", index)

    def test_two_ministers_in_one_article_can_differ(self):
        """A headline match for one minister and a summary-only match for
        another, in the same article."""
        a = article(
            "El ministro de Economía Cuba anuncia medidas",
            "2026-08-01T09:00:00-05:00",
            summary="El ministro de Relaciones Exteriores Espá acompañó el anuncio.",
        )
        index = mn.build_index([a], self.ROSTER, NOW)
        self.assertEqual(index["elmer-rafael-cuba-bustinza"][0]["matched_in"], "title")
        self.assertEqual(
            index["alfonso-carlos-espa-y-garces-alvear"][0]["matched_in"], "summary")


if __name__ == "__main__":
    unittest.main()
