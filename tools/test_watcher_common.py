"""Unit tests for shared watcher helpers (no network)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from watcher_common import dedup_token, normalize


class NormalizeTest(unittest.TestCase):
    def test_lowercases_and_strips_accents(self):
        self.assertEqual(
            normalize("Formalización de la MYPE en el Perú"),
            "formalizacion de la mype en el peru",
        )

    def test_plain_ascii_unchanged(self):
        self.assertEqual(normalize("fuerza popular"), "fuerza popular")


class DedupTokenTest(unittest.TestCase):
    def test_prefix_and_stability(self):
        self.assertEqual(dedup_token("ec", "x"), dedup_token("ec", "x"))
        self.assertTrue(dedup_token("ec", "x").startswith("ec-"))


if __name__ == "__main__":
    unittest.main()
