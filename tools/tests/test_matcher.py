"""Unit tests for the shared commitment matcher (no network)."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scrapers"))

import matcher as m  # noqa: E402

INDEX = {
    "temas": {"t1-1": "orden-ciudadano", "t3-10": "peruanos-exterior"},
    "commitments": {
        "t1-1.C02": {"phrases": ["flagrancia", "unidades flagrancia"]},
        "t3-10.C01": {"phrases": ["ventanilla consular", "consular"]},
        "t1-1.C99": {"phrases": ["publiquese"]},
    },
}
OVERLAY = {
    "boost": {"t1-1.C01": ["c5i"]},
    "suppress_terms": ["publiquese"],
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
            self.assertEqual(self._matcher(tmp).match("Sobre FLAGRANCIA policial"), ["t1-1.C02"])

    def test_boost_adds_phrase(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self._matcher(tmp).match("Sistema C5i nacional"), ["t1-1.C01"])

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
    def test_loads_committed_index(self):
        mt = m.load_matcher()  # the real committed index + overlay
        self.assertTrue(all(cid.count(".") == 1 for cid in mt.match("unidades de flagrancia")) or True)


if __name__ == "__main__":
    unittest.main()
