"""Unit tests for the commitment-index builder (no network)."""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scrapers"))

import build_commitment_index as b  # noqa: E402


class BuildIndexTest(unittest.TestCase):
    # "programa"/"nacional" appear in 4 commitments (DF=4 > df_max_unigram=3) -> generic.
    COMMITMENTS = {
        "t1-1.C02": {"text": "Creación de unidades de flagrancia express", "tema": "t1-1"},
        "t1-1.C04": {"text": "Compra de patrulleros con cámaras inteligentes", "tema": "t1-1"},
        "t2-1.P01": {"text": "Programa nacional de fortalecimiento", "tema": "t2-1"},
        "t2-2.P01": {"text": "Programa nacional de vivienda", "tema": "t2-2"},
        "t2-3.P01": {"text": "Programa nacional de empleo", "tema": "t2-3"},
        "t2-4.P01": {"text": "Programa nacional de salud", "tema": "t2-4"},
    }
    TEMAS = {"t1-1": "orden-ciudadano", "t2-1": "a", "t2-2": "b", "t2-3": "c", "t2-4": "d"}

    def test_distinctive_phrases_survive_generic_dropped(self):
        c = b.build_index(self.COMMITMENTS, self.TEMAS)["commitments"]
        self.assertIn("flagrancia", c["t1-1.C02"]["phrases"])
        self.assertIn("unidades flagrancia", c["t1-1.C02"]["phrases"])
        # "programa"/"nacional" appear in 3 commitments -> generic (DF>df_max_unigram) -> dropped
        self.assertNotIn("programa", c["t2-1.P01"]["phrases"])
        self.assertNotIn("nacional", c["t2-1.P01"]["phrases"])

    def test_temas_map_and_params_structure(self):
        idx = b.build_index(self.COMMITMENTS, self.TEMAS)
        self.assertEqual(idx["temas"]["t1-1"], "orden-ciudadano")
        self.assertEqual(set(idx["params"]), {"df_max_unigram", "df_max_bigram"})

    def test_committed_index_is_in_sync_with_plan(self):
        fresh = b.build_index(b.load_commitments(), b.load_temas())
        committed = json.loads((Path(b.__file__).resolve().parent / "commitment_index.json").read_text())
        self.assertEqual(committed["commitments"], fresh["commitments"])
        self.assertEqual(committed["temas"], fresh["temas"])


if __name__ == "__main__":
    unittest.main()
