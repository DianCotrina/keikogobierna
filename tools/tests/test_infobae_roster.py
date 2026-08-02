"""The cabinet roster survives the cabinet being sworn in.

It read announcements only, which was right while the cabinet was proclaimed
and wrong the moment the gazette seated it: a tenure supersedes its
announcement, the validator then requires the announcement's deletion, and the
roster went to zero. Nothing failed — the profile reader just reported no
material, every run, indistinguishable from a quiet news day. roster() now
lives in cabinet_rules, where both its consumers import it from.
"""

import json
import unittest
from pathlib import Path
from unittest import mock

from tools.scrapers.common import cabinet_rules as cr

MINISTERS = {"ministers": [
    {"slug": "ana-rojas-diaz", "name": "Ana Rojas Díaz", "bio": "Escrita a mano."},
    {"slug": "beto-lima-soto", "name": "Beto Lima Soto", "bio": ""},
    {"slug": "cora-vega-luna", "name": "Cora Vega Luna", "bio": ""},
]}
TENURES = {"tenures": [
    {"person": "ana-rojas-diaz", "portfolio": "pcm", "start": "2026-07-28", "end": None},
    {"person": "beto-lima-soto", "portfolio": "m-salud", "start": "2026-07-28", "end": None},
    {"person": "cora-vega-luna", "portfolio": "m-cultura", "start": "2026-01-01",
     "end": "2026-07-27"},
]}


def with_data(ministers=MINISTERS, tenures=TENURES, announcements=None):
    files = {
        "ministers.json": ministers,
        "tenures.json": tenures,
        "announcements.json": announcements or {"announcements": []},
    }

    class FakeDir:
        def __truediv__(self, name):
            class F:
                def read_text(_self, encoding=None):
                    return json.dumps(files[name], ensure_ascii=False)
            return F()

    return mock.patch.object(cr, "CABINET_DIR", FakeDir())


class RosterTest(unittest.TestCase):
    def test_an_all_appointed_cabinet_still_has_a_roster(self):
        """The regression: no announcements left, and the roster must not empty."""
        with with_data():
            rows = cr.roster()
        self.assertEqual({r["portfolio"] for r in rows}, {"pcm", "m-salud"})

    def test_a_closed_tenure_does_not_put_a_past_holder_on_the_roster(self):
        with with_data():
            rows = cr.roster()
        self.assertNotIn("Cora Vega Luna", [r["person_name"] for r in rows])

    def test_an_announcement_covers_a_cartera_the_gazette_has_not_filled(self):
        announced = {"announcements": [
            {"portfolio": "m-interior", "person_name": "Dino Paz Ruiz", "person": None}]}
        with with_data(announcements=announced):
            rows = cr.roster()
        self.assertIn("m-interior", {r["portfolio"] for r in rows})
        self.assertEqual(len(rows), 3)

    def test_a_tenure_wins_over_a_stale_announcement_for_the_same_cartera(self):
        announced = {"announcements": [
            {"portfolio": "pcm", "person_name": "Nombre De Prensa", "person": None}]}
        with with_data(announcements=announced):
            rows = cr.roster()
        pcm = [r for r in rows if r["portfolio"] == "pcm"]
        self.assertEqual(len(pcm), 1)
        self.assertEqual(pcm[0]["person_name"], "Ana Rojas Díaz")  # the gazette's name

    def test_has_ficha_tracks_a_written_bio_not_mere_existence(self):
        """Every minister has an entry now, so existence stopped being a signal."""
        with with_data():
            rows = {r["person_name"]: r["has_ficha"] for r in cr.roster()}
        self.assertTrue(rows["Ana Rojas Díaz"])
        self.assertFalse(rows["Beto Lima Soto"])

    def test_each_row_carries_the_minister_slug(self):
        """The coverage index keys by slug; the roster is where it comes from."""
        with with_data():
            rows = {r["portfolio"]: r.get("slug") for r in cr.roster()}
        self.assertEqual(rows["pcm"], "ana-rojas-diaz")
        self.assertEqual(rows["m-salud"], "beto-lima-soto")

    def test_an_announced_cartera_has_no_slug(self):
        announced = {"announcements": [
            {"portfolio": "m-interior", "person_name": "Dino Paz Ruiz", "person": None}]}
        with with_data(announcements=announced):
            row = [r for r in cr.roster() if r["portfolio"] == "m-interior"][0]
        self.assertIsNone(row["slug"])


class LiveRosterTest(unittest.TestCase):
    def test_the_committed_cabinet_yields_every_cartera(self):
        rows = cr.roster()
        self.assertEqual(len(rows), 19)
        self.assertEqual(len({r["portfolio"] for r in rows}), 19)


if __name__ == "__main__":
    unittest.main()
