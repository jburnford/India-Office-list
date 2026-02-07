import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from chunking.colonial_office_chunker import ColonialOfficeChunker

DATA_PATH = ROOT / "extracted_json" / "output_a29c9429212df7959632e22b6a667fd55654a592" / "ColonialOfficeList1896.json"
DATA_AVAILABLE = DATA_PATH.exists()


@unittest.skipUnless(DATA_AVAILABLE, f"Test data not found: {DATA_PATH}")
class ColonialOfficeChunkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chunker = ColonialOfficeChunker()
        cls.result = cls.chunker.process_file(DATA_PATH)

    def test_colony_presence(self):
        names = {t["name"] for t in self.result["territories"]}
        self.assertIn("BASUTOLAND", names)
        self.assertIn("BERMUDA", names)
        self.assertIn("THE GOLD COAST COLONY", names)
        self.assertIn("GIBRALTAR", names)
        self.assertIn("Queensland", names)

    def test_domination_grouping(self):
        canada = next((t for t in self.result["territories"] if t["name"] == "DOMINION OF CANADA"), None)
        self.assertIsNotNone(canada, "DOMINION OF CANADA not found")
        subunits = {s["name"] for s in canada.get("subunits", [])}
        self.assertIn("ONTARIO", subunits)
        self.assertIn("MANITOBA AND KEEWATIN", subunits)
        self.assertTrue(any(name.startswith("NORTH WEST") for name in subunits))
        admin_titles = {a["title"] for a in canada.get("admin_sections", [])}
        self.assertIn("THE QUEEN'S PRIVY COUNCIL FOR CANADA", admin_titles)

    def test_sections_detected(self):
        basutoland = next(t for t in self.result["territories"] if t["name"] == "BASUTOLAND")
        section_titles = [section["title"] for section in basutoland["sections"]]
        self.assertIn("Situation and Area.", section_titles)
        self.assertGreaterEqual(len(section_titles), 5)
        self.assertNotIn("BERMUDA", basutoland["text"])
        queensland_entries = [t for t in self.result["territories"] if t["name"] == "Queensland"]
        self.assertGreaterEqual(len(queensland_entries), 1)
        q_primary = queensland_entries[0]

        self.assertGreater(len(q_primary["text"]), 10000)
        queensland_section_titles = [section["title"] for section in q_primary["sections"]]
        self.assertIn("Situation and Area.", queensland_section_titles)
        self.assertEqual(q_primary.get("role"), "primary")
        if len(queensland_entries) > 1:
            q_appendix = queensland_entries[1]
            self.assertEqual(q_appendix.get("role"), "appendix")
            self.assertEqual(q_appendix.get("supplement_for"), q_primary.get("fingerprint"))

    def test_duplicate_name_flagged(self):
        ceylon_entries = [t for t in self.result["territories"] if t["name"] == "CEYLON"]
        self.assertGreaterEqual(len(ceylon_entries), 2)
        primary, appendix = ceylon_entries[0], ceylon_entries[1]
        self.assertEqual(primary.get("role"), "primary")
        self.assertEqual(appendix.get("role"), "appendix")
        self.assertEqual(appendix.get("supplement_for"), primary.get("fingerprint"))

        duplicate_items = [
            item
            for item in self.result["review_queue"]
            if item["name"] == "CEYLON" and "supplementary entry" in item["reason"]
        ]
        self.assertGreaterEqual(len(duplicate_items), 1)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
