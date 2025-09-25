import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from chunking.india_office_chunker import IndiaOfficeChunker

DATA_PATH = ROOT / "il_1892_jan.json"


class IndiaOfficeChunkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chunker = IndiaOfficeChunker()
        cls.result = cls.chunker.process_file(DATA_PATH)

    def test_skips_contents_sections(self):
        titles = {chunk["title"] for chunk in self.result["chunks"]}
        self.assertNotIn("CONTENTS", titles)

    def test_bengal_secretariat_chunk(self):
        target = None
        for chunk in self.result["chunks"]:
            if chunk["title"] == "SECRETARIAT" and "BENGAL" in chunk["section_path"]:
                target = chunk
                break
        self.assertIsNotNone(target, "Bengal Secretariat chunk not found")
        self.assertEqual(target["section_path"][0], "INDIA OFFICE")
        self.assertIn("BENGAL", target["section_path"])
        self.assertGreaterEqual(target["metadata"].get("name_hits", 0), 3)
        self.assertEqual(target["chunk_type"], "roster")

    def test_statistics_include_rosters(self):
        stats = self.result["statistics"]
        self.assertGreater(stats.get("roster", 0), 100)
        self.assertGreater(self.result["total_chunks"], 400)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
