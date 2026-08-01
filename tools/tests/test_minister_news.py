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

    def test_carries_only_the_four_published_fields(self):
        entry = self.index["elmer-rafael-cuba-bustinza"][0]
        self.assertEqual(set(entry), {"title", "url", "source", "published"})

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


if __name__ == "__main__":
    unittest.main()
