"""Reading a JNE hoja de vida into a reviewable draft.

The declarations are self-reported on an inconsistently-completed form, not
court output. In a 220-candidate sample one man declared `delito: TERRORISMO`,
`txFalloPenal: ABSUELTO` and `txModalidad: EFECTIVA` — an acquittal filed under
the modality of an effective prison term. Another filed `delito`, `fallo` and
`órgano` all as the literal string "0".

So nothing here assigns a stage. `draft_person()` emits entries with `stage`
left None and the raw declaration attached, and the cabinet validator refuses
to build while any stage is unset — a person must read the fallo, the modalidad
and the comentario together and decide. That is the same human gate the
norma -> tracking.json path uses.

Fixtures are verbatim captures of the Elecciones Generales 2026 rolls.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scrapers"))

from jne_rules import (  # noqa: E402
    match_candidates,
    draft_person,
    declared_sentences,
    profession_of,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"
ROSTER = json.loads((FIXTURES / "jne_candidatos_eg2026.json").read_text(encoding="utf-8"))
HV_CLEAN = json.loads((FIXTURES / "jne_hv_246699.json").read_text(encoding="utf-8"))
HV_SENTENCED = json.loads((FIXTURES / "jne_hv_252123.json").read_text(encoding="utf-8"))


class MatchCandidates(unittest.TestCase):
    def test_finds_a_minister_by_the_name_the_press_prints(self):
        # Press says "Luis Galarreta"; the roll says "LUIS FERNANDO GALARRETA VELARDE".
        hits = match_candidates("Luis Galarreta", ROSTER)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["idHojaVida"], 246699)

    def test_matching_ignores_accents_and_case(self):
        self.assertTrue(match_candidates("luis galarreta velarde", ROSTER))

    def test_every_query_token_must_appear(self):
        # A partial surname match is not a person match.
        self.assertEqual(match_candidates("Luis Galarreta Quispe", ROSTER), [])

    def test_an_absent_person_matches_nothing(self):
        # Ministers who never ran for office have no hoja de vida at all.
        self.assertEqual(match_candidates("Elmer Cuba Bustinza", ROSTER), [])

    def test_an_ambiguous_query_returns_every_hit_rather_than_guessing(self):
        # One surname alone can match several candidates; the caller must choose.
        hits = match_candidates("Galarreta", ROSTER)
        self.assertGreaterEqual(len(hits), 1)

    def test_duplicate_roll_entries_collapse_to_one_person(self):
        # A candidate appears once per election type in the rolls.
        hits = match_candidates("Luis Galarreta", ROSTER)
        self.assertEqual(len({h["idHojaVida"] for h in hits}), len(hits))

    def test_a_name_match_carries_the_party_so_a_human_can_reject_it(self):
        """Name matching alone is not identity.

        "Carlos Espá" (Fuerza Popular's foreign minister) matches "ALFONSO
        CARLOS ESPA Y GARCES-ALVEAR" of PARTIDO SICREO — a different person
        whose declaration must never be attached to the minister. The match is
        genuine on tokens, so the guard is that every hit reports its party and
        a person confirms before anything is drafted.
        """
        hits = match_candidates("Carlos Espa", ROSTER)
        self.assertTrue(hits)
        for hit in hits:
            self.assertTrue(hit.get("txOrgPol"), "a hit must name its party")
            self.assertTrue(hit.get("idHojaVida"))


class DeclaredSentences(unittest.TestCase):
    def test_a_clean_declaration_yields_no_entries(self):
        self.assertEqual(declared_sentences(HV_CLEAN), [])

    def test_a_declared_sentence_is_read(self):
        entries = declared_sentences(HV_SENTENCED)
        self.assertEqual(len(entries), 1)

    def test_the_stage_is_left_for_a_human(self):
        """The rule this whole module exists for."""
        for entry in declared_sentences(HV_SENTENCED):
            self.assertIsNone(entry["stage"])

    def test_the_charge_is_carried_verbatim(self):
        entry = declared_sentences(HV_SENTENCED)[0]
        self.assertEqual(entry["crime"], "HOMICIDIO CULPOSO")

    def test_the_court_and_file_number_are_carried(self):
        entry = declared_sentences(HV_SENTENCED)[0]
        self.assertEqual(entry["expediente"], "524-2016")
        self.assertIn("CHORRILLOS", entry["body"])

    def test_the_date_is_normalised_to_iso(self):
        # JNE writes dd/mm/yyyy; the schema wants YYYY-MM-DD.
        self.assertEqual(declared_sentences(HV_SENTENCED)[0]["date"], "2016-05-30")

    def test_the_raw_declaration_is_attached_for_the_reviewer(self):
        entry = declared_sentences(HV_SENTENCED)[0]
        raw = entry["_declaracion"]
        for key in ("txFalloPenal", "txModalidad", "txCumpleFallo", "txComentario"):
            self.assertIn(key, raw)

    def test_the_summary_quotes_the_declaration_rather_than_characterising_it(self):
        summary = declared_sentences(HV_SENTENCED)[0]["summary"]
        self.assertIn("declaró", summary.lower())
        self.assertIn("SUSPENDIDA", summary)

    def test_the_source_points_at_the_jne(self):
        source = declared_sentences(HV_SENTENCED)[0]["sources"][0]
        self.assertEqual(source["kind"], "primary")
        self.assertTrue(source["url"].startswith("https://"))


class ContradictoryDeclarations(unittest.TestCase):
    """The cases that make automatic stage mapping unsafe."""

    def test_an_acquittal_filed_as_an_effective_sentence_is_not_labelled(self):
        # Real record: delito TERRORISMO, fallo ABSUELTO, modalidad EFECTIVA.
        hv = {"hv-sentenciapenal": {"sentenciaPenal": [{
            "txExpedientePenal": "1", "feSentenciaPenal": "05/08/2024",
            "txOrganoJudiPenal": "SALA NACIONAL DE TERRORISMO",
            "txDelitoPenal": "TERRORISMO", "txFalloPenal": "ABSUELTO",
            "txModalidad": "EFECTIVA", "txCumpleFallo": "EN CUMPLIMIENTO",
            "txComentario": None, "idHojaVida": 1}]}}
        entry = declared_sentences(hv)[0]
        self.assertIsNone(entry["stage"])
        # Both the acquittal and the contradictory modality must reach the reviewer.
        self.assertIn("ABSUELTO", entry["summary"])
        self.assertIn("EFECTIVA", entry["summary"])

    def test_placeholder_junk_still_produces_a_reviewable_entry(self):
        # Real record: delito, fallo and órgano all the literal string "0".
        hv = {"hv-sentenciapenal": {"sentenciaPenal": [{
            "txExpedientePenal": "0", "feSentenciaPenal": "07/02/2013",
            "txOrganoJudiPenal": "0", "txDelitoPenal": "0", "txFalloPenal": "0",
            "txModalidad": "SUSPENDIDA", "txCumpleFallo": "PENA CUMPLIDA",
            "txComentario": "1. Causa penal prescrita.", "idHojaVida": 1}]}}
        entry = declared_sentences(hv)[0]
        self.assertIsNone(entry["stage"])
        self.assertIn("prescrita", entry["_declaracion"]["txComentario"])


class DraftPerson(unittest.TestCase):
    def setUp(self):
        self.candidate = match_candidates("Luis Galarreta", ROSTER)[0]
        self.draft = draft_person(self.candidate, HV_CLEAN)

    def test_slug_is_kebab_case_and_accent_free(self):
        self.assertEqual(self.draft["slug"], "luis-fernando-galarreta-velarde")

    def test_name_is_title_cased_from_the_roll(self):
        self.assertEqual(self.draft["name"], "Luis Fernando Galarreta Velarde")

    def test_profession_comes_from_the_declared_degree(self):
        self.assertIn("DERECHO", profession_of(HV_CLEAN).upper())

    def test_the_person_carries_a_jne_source(self):
        self.assertTrue(self.draft["sources"])
        self.assertEqual(self.draft["sources"][0]["kind"], "primary")

    def test_a_clean_record_drafts_an_empty_judicial_list(self):
        self.assertEqual(self.draft["judicial"], [])

    def test_a_sentenced_record_drafts_entries_needing_review(self):
        candidate = next(c for c in ROSTER if c["idHojaVida"] == 252123)
        draft = draft_person(candidate, HV_SENTENCED)
        self.assertEqual(len(draft["judicial"]), 1)
        self.assertIsNone(draft["judicial"][0]["stage"])


if __name__ == "__main__":
    unittest.main()
