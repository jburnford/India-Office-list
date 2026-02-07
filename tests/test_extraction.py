"""Tests for the extraction pipeline.

Tests use mock LLM responses — no API key needed.
"""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from extraction.schema import (
    Appointment,
    ChunkExtraction,
    Confidence,
    Honour,
    Location,
    PersonMention,
    Provenance,
)
from extraction.gazetteer import Gazetteer
from extraction.prompts import build_prompt, classify_roster_format, _load_abbreviations
from extraction.extractor import Extractor, _parse_json_response


# ---------------------------------------------------------------------------
# Mock LLM backend
# ---------------------------------------------------------------------------

MOCK_LLM_RESPONSE = json.dumps({
    "persons": [
        {
            "surname": "Cotton",
            "given_names": "H. J. S.",
            "title": None,
            "name_raw": "H. J. S. Cotton, C.S.I.",
            "degrees": [],
            "honours": [
                {"abbreviation": "C.S.I.", "expanded": "Companion of the Order of the Star of India"}
            ],
            "appointments": [
                {
                    "role_raw": "Chief Secretary to Government",
                    "role_expanded": "Chief Secretary to Government",
                    "department": None,
                    "location": "Bengal",
                    "year_appointed": None,
                    "date_start": None,
                    "is_acting": False,
                    "is_officiating": False,
                    "status": None,
                }
            ],
            "confidence": "high",
        },
        {
            "surname": "Risley",
            "given_names": "H. H.",
            "title": None,
            "name_raw": "H. H. Risley, C.I.E.",
            "degrees": [],
            "honours": [
                {"abbreviation": "C.I.E.", "expanded": "Companion of the Order of the Indian Empire"}
            ],
            "appointments": [
                {
                    "role_raw": "Secretary, Financial and Municipal Departments",
                    "role_expanded": "Secretary, Financial and Municipal Departments",
                    "department": "Financial and Municipal Departments",
                    "location": "Bengal",
                    "year_appointed": None,
                }
            ],
            "confidence": "high",
        },
    ],
    "locations": ["Bengal"],
    "year_context": None,
})


def mock_llm(system_prompt: str, user_prompt: str) -> str:
    return MOCK_LLM_RESPONSE


def failing_llm(system_prompt: str, user_prompt: str) -> str:
    raise ConnectionError("API unreachable")


def bad_json_llm(system_prompt: str, user_prompt: str) -> str:
    return "This is not valid JSON at all"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSchema(unittest.TestCase):
    def test_person_mention_defaults(self):
        p = PersonMention(surname="Test", name_raw="Test")
        self.assertEqual(p.degrees, [])
        self.assertEqual(p.honours, [])
        self.assertEqual(p.appointments, [])
        self.assertIsNone(p.canonical_id)

    def test_confidence_enum(self):
        self.assertEqual(Confidence("high"), Confidence.HIGH)
        self.assertEqual(Confidence("low"), Confidence.LOW)

    def test_provenance(self):
        p = Provenance(
            volume="iliol_1896",
            chunk_id="test",
            section_path=["BENGAL", "SECRETARIAT"],
            verbatim_quote="some text",
        )
        self.assertEqual(p.volume, "iliol_1896")


class TestGazetteer(unittest.TestCase):
    def setUp(self):
        self.gaz = Gazetteer()

    def test_bootstrap_populated(self):
        self.assertGreater(len(self.gaz.entries), 30)

    def test_case_insensitive_lookup(self):
        self.assertIsNotNone(self.gaz.lookup("bengal"))
        self.assertIsNotNone(self.gaz.lookup("BENGAL"))
        self.assertIsNotNone(self.gaz.lookup("Bengal"))

    def test_abbreviation_lookup(self):
        entry = self.gaz.lookup("N.W. Provs.")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.canonical, "North-Western Provinces")

    def test_modern_name(self):
        entry = self.gaz.lookup("Cawnpore")
        self.assertEqual(entry.modern_name, "Kanpur")

    def test_unknown_returns_none(self):
        self.assertIsNone(self.gaz.lookup("Xanadu"))

    def test_resolve_shorthand(self):
        self.assertEqual(self.gaz.resolve("C. PROVS."), "Central Provinces")

    def test_add_variant(self):
        self.gaz.add_variant("KOLKATA", "Calcutta")
        self.assertEqual(self.gaz.resolve("KOLKATA"), "Calcutta")

    def test_unresolved(self):
        locs = ["Bengal", "Xanadu", "Calcutta", "Narnia"]
        unresolved = self.gaz.unresolved(locs)
        self.assertEqual(set(unresolved), {"Xanadu", "Narnia"})

    def test_save_and_load(self, tmp_path=None):
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)
        self.gaz.save(path)
        # Load into a fresh gazetteer
        gaz2 = Gazetteer()
        gaz2.load(path)
        self.assertEqual(gaz2.resolve("Bengal"), "Bengal")
        path.unlink()


class TestPrompts(unittest.TestCase):
    def test_abbreviations_load(self):
        abbrevs = _load_abbreviations()
        self.assertIn("C.S.I.", abbrevs)
        self.assertIn("Mag.", abbrevs)

    def test_classify_year_based(self):
        chunk = {
            "text": "1861.\nWard, W. E., C.S.I.\n1862.\nSmith, J.",
            "section_path": ["INDIA AUDIT OFFICE"],
            "chunk_type": "roster",
        }
        self.assertEqual(classify_roster_format(chunk), "roster_year_based")

    def test_classify_role_position(self):
        chunk = {
            "text": "Chief Secretary—H. J. S. Cotton\nUnder Secretary—N. Bonham-Carter\nAssistant—W. Smith\nClerk—J. Brown",
            "section_path": ["BENGAL", "SECRETARIAT"],
            "chunk_type": "roster",
        }
        self.assertEqual(classify_roster_format(chunk), "roster_role_position")

    def test_classify_medical_military(self):
        chunk = {
            "text": "King, George, C.I.E., M.B., Superintendent.\nPurves, H. B.",
            "section_path": ["BENGAL", "BRIGADE SURGEON-LIEUTENANT COLONELS"],
            "chunk_type": "roster",
        }
        self.assertEqual(classify_roster_format(chunk), "roster_medical_military")

    def test_classify_native_civil(self):
        chunk = {
            "text": "1879.\nSardar Gurdial Singh\n1880.\nKunwar Bharat Singh",
            "section_path": ["INDIA AUDIT OFFICE", "NATIVE CIVIL SERVANTS APPOINTED UNDER"],
            "chunk_type": "roster",
        }
        self.assertEqual(classify_roster_format(chunk), "roster_native_civil")

    def test_build_prompt_returns_two_strings(self):
        chunk = {
            "text": "Some text here",
            "section_path": ["BENGAL"],
            "chunk_type": "narrative",
        }
        system, user = build_prompt(chunk, "iliol_1896")
        self.assertIsInstance(system, str)
        self.assertIsInstance(user, str)
        self.assertIn("abbreviation", system.lower())
        self.assertIn("iliol_1896", user)


class TestExtractor(unittest.TestCase):
    def test_extract_chunk_with_mock(self):
        extractor = Extractor(llm=mock_llm, volume="iliol_1896")
        chunk = {
            "title": "SECRETARIAT",
            "section_path": ["BENGAL", "SECRETARIAT"],
            "chunk_type": "roster",
            "text": "Chief Secretary to Government—H. J. S. Cotton, C.S.I.",
        }
        result = extractor.extract_chunk(chunk)
        self.assertIsInstance(result, ChunkExtraction)
        self.assertEqual(len(result.persons), 2)
        self.assertEqual(result.persons[0].surname, "Cotton")
        self.assertEqual(result.persons[0].honours[0].abbreviation, "C.S.I.")
        self.assertEqual(result.persons[1].surname, "Risley")
        self.assertEqual(result.volume, "iliol_1896")

    def test_extract_chunk_llm_failure(self):
        extractor = Extractor(llm=failing_llm, volume="iliol_1896")
        chunk = {
            "title": "TEST",
            "section_path": ["TEST"],
            "chunk_type": "narrative",
            "text": "Some text",
        }
        result = extractor.extract_chunk(chunk)
        self.assertIn("error", result.extraction_metadata)
        self.assertEqual(len(result.persons), 0)

    def test_extract_chunk_bad_json(self):
        extractor = Extractor(llm=bad_json_llm, volume="iliol_1896")
        chunk = {
            "title": "TEST",
            "section_path": ["TEST"],
            "chunk_type": "narrative",
            "text": "Some text",
        }
        result = extractor.extract_chunk(chunk)
        self.assertIn("error", result.extraction_metadata)

    def test_parse_json_with_fences(self):
        raw = '```json\n{"persons": []}\n```'
        parsed = _parse_json_response(raw)
        self.assertEqual(parsed, {"persons": []})

    def test_extract_all_with_limit(self):
        extractor = Extractor(llm=mock_llm, volume="iliol_1896")
        chunks = [
            {"title": f"CHUNK_{i}", "section_path": ["TEST"], "chunk_type": "narrative", "text": "text"}
            for i in range(10)
        ]
        results = extractor.extract_all(chunks, max_chunks=3)
        self.assertEqual(len(results), 3)

    def test_extract_all_progress_callback(self):
        extractor = Extractor(llm=mock_llm, volume="iliol_1896")
        chunks = [
            {"title": f"CHUNK_{i}", "section_path": ["TEST"], "chunk_type": "narrative", "text": "text"}
            for i in range(5)
        ]
        progress_log = []
        results = extractor.extract_all(chunks, on_progress=lambda done, total: progress_log.append((done, total)))
        self.assertEqual(progress_log[-1], (5, 5))


if __name__ == "__main__":
    unittest.main()
