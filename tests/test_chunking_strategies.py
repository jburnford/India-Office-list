"""Unit tests for the core chunking strategies.

These tests use synthetic data so they run without external OCR files.
"""

import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from chunking.chunking_strategies import (
    ReferenceChunker,
    AdministrativeChunker,
    GovernmentReportChunker,
    HybridChunker,
    Chunk,
)
from chunking.document_dna_analyzer import DocumentDNAAnalyzer, DocumentType


class TestReferenceChunker(unittest.TestCase):
    def setUp(self):
        self.chunker = ReferenceChunker(min_size=50, max_size=200)

    def test_basic_chunking(self):
        text = (
            "CABINET, a piece of furniture. "
            "Originally used to store curiosities. " * 5 + "\n"
            "CABLE, a strong rope or chain. "
            "Used in nautical and engineering contexts. " * 5
        )
        chunks = self.chunker.chunk(text, "test_ref")
        # Filter empty chunks (production code does this in the orchestrator)
        chunks = [c for c in chunks if c.text.strip()]
        self.assertGreater(len(chunks), 0)
        for chunk in chunks:
            self.assertIsInstance(chunk, Chunk)

    def test_position_tracking(self):
        text = "ALPHA, first letter.\n" * 20 + "BETA, second letter.\n" * 20
        chunks = self.chunker.chunk(text, "test_pos")
        if len(chunks) > 1:
            # Positions should be monotonically increasing
            for i in range(1, len(chunks)):
                self.assertGreaterEqual(
                    chunks[i].start_pos, chunks[i - 1].start_pos,
                    "Chunk start positions must be non-decreasing"
                )


class TestAdministrativeChunker(unittest.TestCase):
    def setUp(self):
        self.chunker = AdministrativeChunker(min_size=50, max_size=300)

    def test_basic_chunking(self):
        text = (
            "COLONIAL OFFICE DEPARTMENT\n"
            "The Colonial Office oversees territories.\n" * 10 + "\n"
            "TREASURY DEPARTMENT\n"
            "The Treasury manages financial matters.\n" * 10
        )
        chunks = self.chunker.chunk(text, "test_admin")
        self.assertGreater(len(chunks), 0)

    def test_position_tracking_not_zero(self):
        text = (
            "COLONIAL OFFICE DEPARTMENT\n"
            "The Colonial Office oversees all crown colonies and protectorates "
            "across the British Empire. " * 15 + "\n"
            "TREASURY DEPARTMENT\n"
            "Financial administration of colonial territories requires careful "
            "oversight and management. " * 15
        )
        chunks = self.chunker.chunk(text, "test_admin")
        if len(chunks) > 1:
            # At least one chunk after the first should have a non-zero start_pos
            later_starts = [c.start_pos for c in chunks[1:]]
            self.assertTrue(
                any(s > 0 for s in later_starts),
                f"Expected non-zero start positions in later chunks, got {later_starts}"
            )

    def test_colonial_markers_detected(self):
        text = (
            "ADMINISTRATIVE SECTION\n"
            "The Colonial Office manages Crown Colony territories.\n"
            "Governor and Commander in Chief oversees the Protectorate.\n"
            "Her Majesty's Government has jurisdiction over Dependencies.\n"
        )
        chunks = self.chunker.chunk(text, "test_markers")
        # Check that at least one chunk has colonial_discourse_markers
        all_markers = []
        for chunk in chunks:
            all_markers.extend(chunk.metadata.get("colonial_discourse_markers", []))
        self.assertGreater(len(all_markers), 0, "Should detect colonial discourse markers")


class TestGovernmentReportChunker(unittest.TestCase):
    def setUp(self):
        self.chunker = GovernmentReportChunker(min_size=50, max_size=300)

    def test_basic_chunking(self):
        text = (
            "I.\u2014GENERAL ADMINISTRATION\n"
            "The colony was administered efficiently during the year. " * 10 + "\n\n"
            "II.\u2014FINANCIAL REPORT\n"
            "Revenue collected: \u00a3500,000. Expenditure: \u00a3450,000. " * 10
        )
        chunks = self.chunker.chunk(text, "test_report")
        self.assertGreater(len(chunks), 0)

    def test_position_tracking(self):
        text = (
            "I.\u2014GENERAL ADMINISTRATION\n"
            "The colony was administered efficiently during the reporting period. " * 20 + "\n\n"
            "II.\u2014FINANCIAL REPORT\n"
            "Revenue collection and expenditure management continued throughout. " * 20
        )
        chunks = self.chunker.chunk(text, "test_report")
        if len(chunks) > 1:
            later_starts = [c.start_pos for c in chunks[1:]]
            self.assertTrue(
                any(s > 0 for s in later_starts),
                f"Expected non-zero start positions in later chunks, got {later_starts}"
            )


class TestHybridChunker(unittest.TestCase):
    def setUp(self):
        self.chunker = HybridChunker(min_size=50, max_size=200)

    def test_basic_chunking(self):
        text = "This is sentence one. This is sentence two. " * 20
        chunks = self.chunker.chunk(text, "test_hybrid")
        self.assertGreater(len(chunks), 0)

    def test_position_tracking(self):
        text = "The quick brown fox jumped over the lazy dog. " * 30
        chunks = self.chunker.chunk(text, "test_hybrid")
        if len(chunks) > 1:
            # First chunk starts at or near 0
            self.assertLessEqual(chunks[0].start_pos, 1)
            # Later chunks have increasing positions
            for i in range(1, len(chunks)):
                self.assertGreater(
                    chunks[i].start_pos, chunks[i - 1].start_pos,
                    "Chunk start positions should be strictly increasing"
                )
            # Last chunk ends at or near the end of text
            self.assertGreaterEqual(chunks[-1].end_pos, len(text) - 50)

    def test_sentence_count_metadata(self):
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        chunks = self.chunker.chunk(text, "test_meta")
        for chunk in chunks:
            self.assertIn("sentence_count", chunk.metadata)
            self.assertGreater(chunk.metadata["sentence_count"], 0)


class TestDocumentDNAAnalyzer(unittest.TestCase):
    def test_reference_detection(self):
        analyzer = DocumentDNAAnalyzer()
        doc = {
            "text": (
                "CABINET, a piece of furniture used for storage.\n"
                "CABLE, a strong rope or chain.\n"
                "CADIZ, a city in Spain.\n"
            ) * 20,
        }
        profile = analyzer.analyze(doc)
        self.assertEqual(profile.document_type, DocumentType.REFERENCE)

    def test_administrative_detection(self):
        analyzer = DocumentDNAAnalyzer()
        doc = {
            "text": (
                "COLONIAL OFFICE\n"
                "Governor and Commander in Chief\n"
                "Secretary of State for the Colonies\n"
                "Crown Colony | Protectorate | Dependencies\n"
            ) * 20,
        }
        profile = analyzer.analyze(doc)
        self.assertIn(profile.document_type, [DocumentType.ADMINISTRATIVE, DocumentType.HYBRID])


if __name__ == "__main__":
    unittest.main()
