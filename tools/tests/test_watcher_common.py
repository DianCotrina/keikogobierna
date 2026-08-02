"""Unit tests for shared watcher helpers (no network)."""

import unittest
from pathlib import Path


from tools.scrapers.common.watcher_common import dedup_token, normalize, phrases_of, significant_tokens


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


class TokenizeTest(unittest.TestCase):
    def test_drops_stopwords_short_and_folds_accents(self):
        self.assertEqual(significant_tokens("de la MYPE en el Perú"), ["mype", "peru"])

    def test_extra_stop_removes_extra_terms(self):
        self.assertEqual(significant_tokens("comuniquese y publiquese la norma",
                                            extra_stop={"comuniquese", "publiquese"}), ["norma"])

    def test_phrases_are_unigrams_and_adjacent_bigrams(self):
        self.assertEqual(
            phrases_of(["unidades", "flagrancia", "express"]),
            {"unidades", "flagrancia", "express", "unidades flagrancia", "flagrancia express"},
        )

    def test_bigram_survives_dropped_stopword(self):
        self.assertIn("unidades flagrancia", phrases_of(significant_tokens("unidades de flagrancia")))

    def test_keeps_short_acronyms_with_a_digit(self):
        # "c5i" is 3 chars but distinctive; "ley" (no digit, 3 chars) is dropped
        self.assertEqual(significant_tokens("Sistema C5i para la ley"), ["sistema", "c5i"])

    def test_punctuation_does_not_leak_into_tokens(self):
        self.assertEqual(significant_tokens("a Nivel Nacional, correspondiente"),
                         ["nivel", "nacional", "correspondiente"])

    def test_bigram_survives_intervening_punctuation(self):
        # A norma writing "unidades de flagrancia," must still hit the indexed
        # "unidades flagrancia" — otherwise punctuation silently costs us recall.
        self.assertIn("unidades flagrancia",
                      phrases_of(significant_tokens("crea unidades de flagrancia, en Lima")))


if __name__ == "__main__":
    unittest.main()
