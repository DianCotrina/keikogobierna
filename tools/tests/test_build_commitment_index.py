"""Unit tests for the commitment-index builder (no network)."""

import json
import unittest
from pathlib import Path


from tools.scrapers import build_commitment_index as b  # noqa: E402


class BuildIndexTest(unittest.TestCase):
    COMMITMENTS = {
        "t1-1.C02": "Creación de unidades de flagrancia express",
        "t1-1.C04": "Compra de patrulleros con cámaras inteligentes",
        "t2-1.P01": "Programa nacional de fortalecimiento",
        "t2-2.P01": "Programa nacional de vivienda",
        "t2-3.P01": "Programa nacional de empleo",
        "t2-4.P01": "Programa nacional de salud",
    }
    TEMAS = {"t1-1": "orden-ciudadano", "t2-1": "a", "t2-2": "b", "t2-3": "c", "t2-4": "d"}

    def test_phrases_are_distinctive_bigrams_only(self):
        c = b.build_index(self.COMMITMENTS, self.TEMAS)["commitments"]
        self.assertIn("unidades flagrancia", c["t1-1.C02"]["phrases"])
        # every phrase is a bigram — single words are never emitted (too ambiguous)
        for entry in c.values():
            self.assertTrue(all(" " in p for p in entry["phrases"]), entry["phrases"])

    def test_temas_map_and_params_structure(self):
        idx = b.build_index(self.COMMITMENTS, self.TEMAS)
        self.assertEqual(idx["temas"]["t1-1"], "orden-ciudadano")
        self.assertEqual(set(idx["params"]), {"df_max_bigram"})

    def test_committed_index_is_in_sync_with_plan(self):
        fresh = b.build_index(*b.load_plan())
        committed = json.loads((Path(b.__file__).resolve().parent / "commitment_index.json").read_text())
        self.assertEqual(committed["commitments"], fresh["commitments"])
        self.assertEqual(committed["temas"], fresh["temas"])


if __name__ == "__main__":
    unittest.main()
