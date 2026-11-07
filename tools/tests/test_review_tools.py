"""Review tools against real captured El Peruano data (no hand-made fixtures)."""

import json
import unittest
from pathlib import Path

from tools.review.archive_search import normalize
from tools.review.fetch_norma import page_field

FIXTURES = Path(__file__).parent / "fixtures" / "review"


class PageFieldTest(unittest.TestCase):
    raw = (FIXTURES / "page_data_245_2026_ef.txt").read_text()

    def test_reads_the_pdf_path(self):
        self.assertEqual(page_field(self.raw, "urlPDF"), "/api/archivo/file/9wl6X60KaJwBlecfiwkyaU/*/2571878-1.PDF")

    def test_decodes_accents(self):
        self.assertTrue(page_field(self.raw, "sumilla").startswith("Decreto Supremo que aprueba el Texto Único"))

    def test_missing_field_is_none(self):
        self.assertIsNone(page_field(self.raw, "noExiste"))


class ArchiveNormalizeTest(unittest.TestCase):
    def test_legacy_record(self):
        record = json.loads((FIXTURES / "archive_legacy.jsonl").read_text())
        self.assertEqual(normalize(record), ("2026-07-14", "2533006-1"))

    def test_current_record(self):
        record = json.loads((FIXTURES / "archive_current.jsonl").read_text())
        self.assertEqual(normalize(record), ("2026-08-28", "2548029-1"))


if __name__ == "__main__":
    unittest.main()
