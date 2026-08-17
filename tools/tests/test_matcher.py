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

    def test_a_multiword_boost_does_not_leak_its_words(self):
        # Boosting "ejecutor compras" for Compras MyPerú used to index a bare
        # "compras" as well, and PERÚ COMPRAS puts that word in the *number* of
        # every resolution it publishes — so the agency's whole output matched
        # the commitment (issues #316, #317).
        overlay = {**OVERLAY, "boost": {"t2-1.P01": ["ejecutor compras"]}}
        with tempfile.TemporaryDirectory() as tmp:
            mt = self._matcher(tmp, overlay)
            self.assertEqual(mt.match("Aprueban modificación de Fichas Técnicas del "
                                      "Catálogo Electrónico de Acuerdos Marco"), [])
            self.assertEqual(mt.match("Designan Ejecutor Coactivo de la municipalidad"), [])
            self.assertEqual(mt.match("Transferencia al Núcleo Ejecutor de Compras"),
                             ["t2-1.P01"])

    def test_a_boost_longer_than_a_bigram_still_matches(self):
        # A norma only ever yields unigrams and bigrams, so a three-token boost
        # has to reach the index as its adjacent bigrams or it could never match.
        overlay = {**OVERLAY, "boost": {"t2-1.P01": ["nucleo ejecutor compras"]}}
        with tempfile.TemporaryDirectory() as tmp:
            mt = self._matcher(tmp, overlay)
            self.assertEqual(mt.match("Transferencia al Núcleo Ejecutor de Compras"),
                             ["t2-1.P01"])
            self.assertEqual(mt.match("Aprueban Fichas Técnicas de compras"), [])

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


class GenericPhraseRegressionTest(unittest.TestCase):
    """Real normas that reached the review queue on 2026-08-01/02 as false positives.

    Each matched on a boilerplate bigram that says nothing about a commitment
    ("fondo nacional", "nivel nacional"). Issues #228-#234; see the overlay's
    suppress_phrases. They must produce no match at all.
    """

    NOISE = {
        # issue: (numero, tipo, sumilla)  -- the exact text the scraper matches on
        229: ("N° 176-2026-INEI", "RESOLUCIÓN JEFATURAL",
              "Índice de Precios al Por Mayor a Nivel Nacional, correspondiente al mes de julio de 2026"),
        230: ("N° 175-2026-INEI", "RESOLUCIÓN JEFATURAL",
              "Índices de Precios al Consumidor a Nivel Nacional y de Lima Metropolitana, "
              "correspondientes al mes de julio 2026"),
        234: ("N° 422-2026-CG", "RESOLUCIÓN",
              "Modifican el Anexo N° 1 de la Resolución de Contraloría N° 237-2021-CG, a fin de "
              "incluir al Fondo Nacional de Financiamiento de la Actividad Empresarial del Estado - FONAFE"),
        232: ("N° 2265-2026-MP-FN", "RESOLUCIÓN",
              "Nombran y designan fiscales en los Distritos Judiciales de Lima Centro y La Libertad"),
        233: ("N° 000611-2026-P-CSNJPE-PJ", "RESOLUCIÓN ADMINISTRATIVA",
              "Oficializan incorporación de magistrado como juez a cargo del Primer Juzgado de "
              "Investigación Preparatoria Nacional de la Corte Superior Nacional de Justicia Penal Especializada"),
        231: ("N° Definitiva N° 211-2025-AREQUIPA", "INVESTIGACION",
              "Imponen medida disciplinaria de destitución a juez de los Juzgados de Paz de 15 de Agosto, "
              "Jorge Chávez, Ciudad Blanca y Progresista de Paucarpata, y de los Juzgados de Primera "
              "Nominación, Segunda Nominación y Santa Rosa"),
        228: ("N° 245-2026-PCM", "RESOLUCIÓN SUPREMA",
              "Designan Director de Inteligencia Nacional de la Dirección Nacional de Inteligencia - DINI"),
    }

    def test_boilerplate_normas_do_not_match_any_commitment(self):
        mt = m.load_matcher()
        for issue, (numero, tipo, sumilla) in sorted(self.NOISE.items()):
            with self.subTest(issue=issue):
                self.assertEqual(mt.match(f"{numero} {tipo} {sumilla}"), [],
                                 f"issue #{issue} should no longer reach the review queue")

    def test_suppressing_generic_heads_keeps_the_distinctive_tail(self):
        # Each suppressed phrase is a generic head; the norma that genuinely
        # evidences the commitment still carries the specific tail that names it.
        mt = m.load_matcher()
        for label, text in (
            ("FONIEX", "Lanzan el Fondo Nacional de Innovación Exportadora para agroindustria"),
            # "jorge chavez"/"santa rosa" are suppressed as court names, but a real
            # airport norma says "aeropuerto" — that is what must still carry it.
            ("aeropuertos", "Aprueban la modernización de los aeropuertos concesionados "
                            "priorizando seguridad aérea y capacidad operativa"),
        ):
            with self.subTest(label=label):
                self.assertTrue(mt.match(text),
                                "suppressing a generic head must not blind the matcher to the tail")


if __name__ == "__main__":
    unittest.main()
