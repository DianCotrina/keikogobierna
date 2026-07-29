"""Matching press items to the minister they profile.

Fixture is the real Infobae Peru feed captured 2026-07-28, the evening the
cabinet was sworn in. Nothing here is invented: every headline asserted on was
actually published.
"""
import unittest
from pathlib import Path

from tools.scrapers.common import press_feeds
from tools.scrapers.common.infobae_rules import is_profile, profile_items

FIXTURE = (Path(__file__).resolve().parent / "fixtures" / "infobae_peru_20260728.xml").read_bytes()
ARTICLES = press_feeds.parse_feed(FIXTURE, "Infobae")

ROSTER = [
    {"portfolio": "pcm", "person_name": "Luis Galarreta Velarde"},
    {"portfolio": "m-economia", "person_name": "Elmer Cuba Bustinza"},
    {"portfolio": "m-relaciones-exteriores", "person_name": "Carlos Espá y Garcés-Alvear"},
    {"portfolio": "m-defensa", "person_name": "Rafael Belaunde Llosa"},
    {"portfolio": "m-interior", "person_name": "César Astudillo Salcedo"},
    {"portfolio": "m-agrario", "person_name": "Marco Vinelli Ruiz"},
    {"portfolio": "m-energia-minas", "person_name": "Guillermo Shinno Huamaní"},
    {"portfolio": "m-transportes", "person_name": "Rafael Rey Rey"},
    {"portfolio": "m-salud", "person_name": "Luis Dyer Fernández"},
    {"portfolio": "m-educacion", "person_name": "José Antonio Chang Escobedo"},
    {"portfolio": "m-cultura", "person_name": "Alberto Beingolea Delgado"},
    {"portfolio": "m-ambiente", "person_name": "Vladimiro Huaroc Portocarrero"},
    {"portfolio": "m-mujer", "person_name": "Mara Seminario Marón"},
    {"portfolio": "m-comercio-exterior", "person_name": "Roger Valencia Espinoza"},
    {"portfolio": "m-trabajo", "person_name": "Juan Sheput Moore"},
    {"portfolio": "m-vivienda", "person_name": "Mauricio Arnillas Gonzales"},
    {"portfolio": "m-justicia", "person_name": "Ernesto Álvarez Miranda"},
    {"portfolio": "m-desarrollo-social", "person_name": "Maritza Canales Martínez"},
    {"portfolio": "m-produccion", "person_name": "Juan Carlos Requejo Alemán"},
]

FOUND = profile_items(ARTICLES, ROSTER)


class Coverage(unittest.TestCase):
    def test_most_of_the_cabinet_is_covered(self):
        self.assertGreaterEqual(len(FOUND), 12, sorted(FOUND))

    def test_every_key_is_a_roster_portfolio(self):
        self.assertTrue(set(FOUND) <= {r["portfolio"] for r in ROSTER})

    def test_no_cartera_comes_back_empty(self):
        for pid, items in FOUND.items():
            self.assertTrue(items, pid)


class MatchingIsTwoKeyed(unittest.TestCase):
    def test_a_given_name_variant_still_matches_on_surname_plus_cartera(self):
        # The roster says "Mara Seminario Marón"; Infobae writes "María
        # Seminario". Name-only matching loses her; the cartera saves it.
        self.assertIn("m-mujer", FOUND)

    def test_a_shared_surname_without_a_cartera_matches_nothing(self):
        # "Guardaespaldas del Rey de España se roba la atención" carries the
        # surname of the transport minister and names no ministry at all.
        for item in FOUND.get("m-transportes", []):
            self.assertNotIn("guardaespaldas", item["title"].lower())

    def test_an_unrelated_item_is_never_matched(self):
        for items in FOUND.values():
            for item in items:
                self.assertNotIn("Copa Federación", item["title"])


class Ranking(unittest.TestCase):
    def test_a_profile_piece_outranks_plain_news(self):
        for pid, items in FOUND.items():
            profiles = [i for i, it in enumerate(items) if is_profile(it["title"])]
            if profiles and len(items) > 1:
                self.assertEqual(profiles[0], 0, f"{pid}: {items[0]['title']}")

    def test_is_profile_recognises_the_usual_shapes(self):
        self.assertTrue(is_profile("¿Quién es Marco Vinelli Ruiz? Perfil y hoja de vida"))
        self.assertTrue(is_profile("Conoce a Juan Carlos Requejo, nuevo titular de Produce"))
        self.assertTrue(is_profile("Juan Sheput asume el Ministerio de Trabajo: trayectoria política"))
        self.assertFalse(is_profile("Perú expresa solidaridad con Japón tras terremoto"))


class Purity(unittest.TestCase):
    def test_the_matcher_never_reads_an_article_body(self):
        # The feed carries content:encoded; parse_feed does not expose it and
        # nothing here may reintroduce it.
        for items in FOUND.values():
            for item in items:
                self.assertEqual(set(item),
                                 {"title", "url", "summary", "author", "published", "source"})

    def test_an_empty_roster_matches_nothing(self):
        self.assertEqual(profile_items(ARTICLES, []), {})

    def test_no_articles_is_safe(self):
        self.assertEqual(profile_items([], ROSTER), {})


if __name__ == "__main__":
    unittest.main()
