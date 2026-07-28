"""Integrity rules for src/data/cabinet/.

The rule that matters most: a judicial entry without a source must fail the
build. These are named living people, and an unsourced accusation should be
impossible to publish by accident rather than merely discouraged.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cabinet"))

from validate_cabinet_data import validate  # noqa: E402

TOPICS = {"t1-1", "t3-3"}
PORTFOLIOS = [
    {"id": "m-interior", "name": "Ministerio del Interior", "short": "Interior",
     "slug": "interior", "topics": ["t1-1"]},
    {"id": "m-salud", "name": "Ministerio de Salud", "short": "Salud",
     "slug": "salud", "topics": ["t3-3"]},
]
SOURCE = {"label": "Poder Judicial", "url": "https://example.pe/exp", "kind": "primary"}


def person(**overrides):
    base = {"slug": "ana-torres", "name": "Ana Torres", "profession": "Abogada",
            "bio": "Dos frases neutrales.", "sources": [SOURCE], "judicial": []}
    base.update(overrides)
    return base


def tenure(**overrides):
    base = {"person": "ana-torres", "portfolio": "m-interior", "start": "2026-07-28",
            "end": None, "appointment_norma": {"numero": "R.S. N° 001-2026-PCM",
                                               "url": "https://example.pe/rs", "date": "2026-07-28"},
            "exit_norma": None, "exit_reason": None}
    base.update(overrides)
    return base


def entry(**overrides):
    base = {"id": "caso-01", "case": "Caso X", "stage": "acusacion_fiscal",
            "crime": "colusión", "body": "Fiscalía", "date": "2026-03-01",
            "summary": "Hechos.", "sources": [SOURCE]}
    base.update(overrides)
    return base


def announcement(**overrides):
    base = {"portfolio": "m-salud", "person_name": "Luis Galarreta",
            "announced": "2026-07-27",
            "sources": [{"label": "El Comercio", "url": "https://elcomercio.pe/x", "kind": "press"}]}
    base.update(overrides)
    return base


def run(portfolios=None, people=None, tenures=None, announcements=None):
    return validate(portfolios if portfolios is not None else PORTFOLIOS,
                    people if people is not None else [person()],
                    tenures if tenures is not None else [tenure()],
                    TOPICS,
                    announcements=announcements if announcements is not None else [])


class ValidCase(unittest.TestCase):
    def test_a_well_formed_dataset_passes(self):
        self.assertEqual(run(), [])

    def test_an_empty_roster_is_valid(self):
        self.assertEqual(run(people=[], tenures=[]), [])


class JudicialRules(unittest.TestCase):
    def test_an_entry_without_sources_fails(self):
        errors = run(people=[person(judicial=[entry(sources=[])])])
        self.assertTrue(any("source" in e for e in errors), errors)

    def test_an_entry_missing_the_sources_key_fails(self):
        bad = entry()
        del bad["sources"]
        self.assertTrue(run(people=[person(judicial=[bad])]))

    def test_a_non_https_source_fails(self):
        errors = run(people=[person(judicial=[entry(
            sources=[{"label": "x", "url": "http://example.pe", "kind": "press"}])])])
        self.assertTrue(any("https" in e for e in errors), errors)

    def test_an_unknown_source_kind_fails(self):
        errors = run(people=[person(judicial=[entry(
            sources=[{"label": "x", "url": "https://example.pe", "kind": "rumor"}])])])
        self.assertTrue(any("kind" in e for e in errors), errors)

    def test_an_unknown_stage_fails(self):
        errors = run(people=[person(judicial=[entry(stage="culpable")])])
        self.assertTrue(any("stage" in e for e in errors), errors)

    def test_a_jne_draft_with_an_unset_stage_cannot_be_merged(self):
        # jne_scraper emits entries with stage None on purpose: the declaration
        # is self-reported and its fields contradict each other, so a person
        # must classify each one. This is what stops a draft reaching the site.
        errors = run(people=[person(judicial=[entry(stage=None)])])
        self.assertTrue(any("stage" in e for e in errors), errors)

    def test_a_missing_stage_key_also_fails(self):
        draft = entry()
        del draft["stage"]
        self.assertTrue(run(people=[person(judicial=[draft])]))

    def test_duplicate_entry_ids_within_one_person_fail(self):
        errors = run(people=[person(judicial=[entry(), entry()])])
        self.assertTrue(any("duplicate" in e.lower() for e in errors), errors)

    def test_a_future_date_fails(self):
        errors = run(people=[person(judicial=[entry(date="2999-01-01")])])
        self.assertTrue(any("future" in e.lower() for e in errors), errors)

    def test_a_malformed_date_fails(self):
        self.assertTrue(run(people=[person(judicial=[entry(date="01/03/2026")])]))


class TenureRules(unittest.TestCase):
    def test_an_unknown_person_reference_fails(self):
        errors = run(tenures=[tenure(person="ghost")])
        self.assertTrue(any("ghost" in e for e in errors), errors)

    def test_an_unknown_portfolio_reference_fails(self):
        self.assertTrue(run(tenures=[tenure(portfolio="m-nope")]))

    def test_a_missing_appointment_norma_fails(self):
        errors = run(tenures=[tenure(appointment_norma=None)])
        self.assertTrue(any("appointment_norma" in e for e in errors), errors)

    def test_end_before_start_fails(self):
        self.assertTrue(run(tenures=[tenure(start="2026-09-01", end="2026-08-01")]))

    def test_a_future_start_is_allowed(self):
        # An appointment norma is published with an effective date, so a tenure
        # can legitimately begin tomorrow. Unlike a judicial date, which cannot.
        self.assertEqual(run(tenures=[tenure(start="2099-01-01")]), [])

    def test_two_open_tenures_on_one_portfolio_fail(self):
        people = [person(), person(slug="beto-lima", name="Beto Lima")]
        errors = run(people=people,
                     tenures=[tenure(), tenure(person="beto-lima")])
        self.assertTrue(any("open" in e.lower() for e in errors), errors)

    def test_overlapping_tenures_on_one_portfolio_fail(self):
        people = [person(), person(slug="beto-lima", name="Beto Lima")]
        errors = run(people=people, tenures=[
            tenure(end="2026-10-01"),
            tenure(person="beto-lima", start="2026-09-01", end="2026-11-01"),
        ])
        self.assertTrue(any("overlap" in e.lower() for e in errors), errors)

    def test_consecutive_tenures_on_one_portfolio_are_fine(self):
        people = [person(), person(slug="beto-lima", name="Beto Lima")]
        self.assertEqual(run(people=people, tenures=[
            tenure(end="2026-10-01"),
            tenure(person="beto-lima", start="2026-10-01", end=None),
        ]), [])


class RegistryRules(unittest.TestCase):
    def test_a_portfolio_topic_outside_the_plan_fails(self):
        bad = [dict(PORTFOLIOS[0], topics=["t9-9"]), PORTFOLIOS[1]]
        errors = run(portfolios=bad)
        self.assertTrue(any("t9-9" in e for e in errors), errors)

    def test_duplicate_person_slugs_fail(self):
        errors = run(people=[person(), person()])
        self.assertTrue(any("duplicate" in e.lower() for e in errors), errors)

    def test_duplicate_portfolio_ids_fail(self):
        self.assertTrue(run(portfolios=[PORTFOLIOS[0], PORTFOLIOS[0]]))


class AnnouncementRules(unittest.TestCase):
    """Provisional entries still carry a source -- the whole point is that a
    reader can check the claim against the outlet that made it."""

    def test_a_well_formed_announcement_passes(self):
        self.assertEqual(run(announcements=[announcement()]), [])

    def test_an_announcement_without_sources_fails(self):
        errors = run(announcements=[announcement(sources=[])])
        self.assertTrue(any("source" in e for e in errors), errors)

    def test_an_announcement_source_must_be_press(self):
        # A gazette-sourced entry belongs in tenures.json, not here.
        errors = run(announcements=[announcement(
            sources=[{"label": "El Peruano", "url": "https://x.pe", "kind": "primary"}])])
        self.assertTrue(any("press" in e for e in errors), errors)

    def test_an_unknown_portfolio_fails(self):
        self.assertTrue(run(announcements=[announcement(portfolio="m-nope")]))

    def test_a_missing_person_name_fails(self):
        self.assertTrue(run(announcements=[announcement(person_name="")]))

    def test_two_announcements_for_one_portfolio_fail(self):
        errors = run(announcements=[announcement(), announcement()])
        self.assertTrue(any("duplicate" in e.lower() for e in errors), errors)

    def test_an_announcement_may_name_a_verified_person(self):
        self.assertEqual(run(announcements=[announcement(person="ana-torres")]), [])

    def test_an_announcement_naming_an_unknown_person_fails(self):
        errors = run(announcements=[announcement(person="ghost")])
        self.assertTrue(any("ghost" in e for e in errors), errors)

    def test_an_announcement_for_an_already_served_portfolio_fails(self):
        # m-interior has an open tenure in the default fixture: the gazette has
        # spoken, so the provisional entry must be removed rather than linger.
        errors = run(announcements=[announcement(portfolio="m-interior")])
        self.assertTrue(any("superseded" in e.lower() for e in errors), errors)


class RealDataTest(unittest.TestCase):
    def test_the_committed_cabinet_data_is_valid(self):
        import validate_cabinet_data as v
        self.assertEqual(v.validate(*v.load_all()), [])


if __name__ == "__main__":
    unittest.main()
