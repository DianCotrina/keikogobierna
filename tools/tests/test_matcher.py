"""Unit tests for the shared commitment matcher (no network)."""

import json
import tempfile
import unittest
from pathlib import Path


from tools.scrapers.common import matcher as m  # noqa: E402

INDEX = {
    "temas": {"t1-1": "orden-ciudadano", "t3-10": "peruanos-exterior"},
    "commitments": {
        "t1-1.C02": {"phrases": ["unidades flagrancia"]},
        "t3-10.C01": {"phrases": ["ventanilla consular"]},
        "t2-1.P01": {"phrases": ["poder judicial"]},
    },
}
OVERLAY = {
    "boost": {"t1-1.C01": ["c5i"]},
    "suppress_terms": ["publiquese"],
    "suppress_phrases": ["poder judicial"],
    "mute_commitments": ["t3-10.C01"],
}


def _write(tmp, name, obj):
    p = Path(tmp) / name
    p.write_text(json.dumps(obj), encoding="utf-8")
    return p


class MatcherTest(unittest.TestCase):
    def _matcher(self, tmp, overlay=OVERLAY):
        return m.load_matcher(_write(tmp, "i.json", INDEX), _write(tmp, "o.json", overlay))

    def test_bigram_matches_across_dropped_stopword(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self._matcher(tmp).match("Autorizan unidades de flagrancia en Lima"), ["t1-1.C02"])

    def test_accent_and_case_insensitive(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self._matcher(tmp).match("Nuevas UNIDADES de FLAGRANCIA"), ["t1-1.C02"])

    def test_lone_unigram_does_not_match(self):
        # "flagrancia" alone (no adjacent "unidades") is not a bigram -> no match
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self._matcher(tmp).match("Regimen de flagrancia policial"), [])

    def test_boost_adds_phrase(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self._matcher(tmp).match("Sistema C5i nacional"), ["t1-1.C01"])

    def test_suppress_phrase_ignores_generic_bigram(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self._matcher(tmp).match("Designan jefe del poder judicial"), [])

    def test_mute_commitment_removes_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self._matcher(tmp).match("Nueva ventanilla consular"), [])

    def test_mute_by_tema_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            mt = self._matcher(tmp, overlay={"mute_commitments": ["t1-1"]})
            self.assertEqual(mt.match("unidades de flagrancia"), [])  # whole tema muted

    def test_suppress_term_never_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self._matcher(tmp).match("Registrese y publiquese"), [])

    def test_tema_slug_from_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self._matcher(tmp).tema_slug("t1-1.C02"), "orden-ciudadano")

    def test_no_match_is_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self._matcher(tmp).match("Feria dominical de artesanos"), [])


class RealIndexTest(unittest.TestCase):
    def test_committed_index_matches_a_distinctive_phrase(self):
        mt = m.load_matcher()  # the real committed index + overlay
        ids = mt.match("Autorizan la creación de unidades de flagrancia")
        self.assertTrue(ids, "a distinctive plan bigram should match at least one commitment")
        self.assertTrue(all(cid.count(".") == 1 for cid in ids))  # well-formed commitment ids


if __name__ == "__main__":
    unittest.main()
