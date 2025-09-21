"""
Document DNA Analyzer - Detects document types for adaptive chunking strategy selection.

This module implements the "Document DNA Detection" system described in the adaptive
chunking framework. It analyzes document structure, content patterns, and metadata
to classify historical documents into appropriate types for specialized chunking.
"""

import json
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class DocumentType(Enum):
    REFERENCE = "reference"          # Encyclopædia Britannica, dictionaries
    ADMINISTRATIVE = "administrative" # Colonial Office Lists, personnel records
    GOVERNMENT_REPORT = "government_report"  # Annual reports, colonial reports
    NARRATIVE = "narrative"          # Crime reports, correspondence
    LEGAL = "legal"                  # Court records, legal documents
    HYBRID = "hybrid"                # Mixed or unknown documents

@dataclass
class DocumentProfile:
    """Profile containing document analysis results."""
    document_type: DocumentType
    confidence: float
    features: Dict[str, any]
    metadata: Dict[str, any]
    suggested_chunk_size: Tuple[int, int]  # (min, max) characters

class DocumentDNAAnalyzer:
    """Analyzes document structure and content to determine optimal chunking strategy."""

    def __init__(self):
        # Patterns for different document types
        self.reference_patterns = [
            r'^[A-Z]{2,}\b',  # All-caps headings (CABO, CABINET)
            r'\b(See|see)\s+[A-Z][a-z]+\.',  # Cross-references
            r'^\s*[A-Z][A-Z\s]+[A-Z]\s*,',  # Entry headers
            r'in\s+(botany|medicine|theology|geography)',  # Subject classifications
        ]

        self.administrative_patterns = [
            r'Colonial\s+Office',
            r'Secretary\s+of\s+State',
            r'H\.?\s*M\.?\s*Government',
            r'Governor\s+and\s+Commander',
            r'\b(Chief|Assistant|Deputy)\s+(Commissioner|Secretary)',
            r'(\£|\$)\s*\d+[,\d]*',  # Salary figures
            r'^\s*\|[^|]*\|',  # Table rows
        ]

        self.government_report_patterns = [
            r'REPORT\s+FOR\s+\d{4}',
            r'COLONIAL\s+REPORTS',
            r'(Revenue|Expenditure|Financial)',
            r'His\s+Majesty[\'\u2019]?s\s+Government',
            r'^\s*I\.—|II\.—|III\.—',  # Roman numeral sections
            r'ADMINISTRATION|ESTABLISHMENT',
        ]

    def analyze(self, document: Dict) -> DocumentProfile:
        """
        Analyze a document to determine its type and characteristics.

        Args:
            document: Dictionary containing 'text' and optionally 'id', 'metadata'

        Returns:
            DocumentProfile with analysis results
        """
        text = document.get('text', '')
        doc_id = document.get('id', 'unknown')

        # Extract features for analysis
        features = self._extract_features(text)

        # Classify document type
        doc_type, confidence = self._classify_document(text, features)

        # Determine suggested chunk size based on type
        chunk_size = self._suggest_chunk_size(doc_type, features)

        # Extract metadata
        metadata = {
            'id': doc_id,
            'text_length': len(text),
            'line_count': text.count('\n'),
            'has_tables': features['table_density'] > 0.01,
            'colonial_markers': features['colonial_markers'],
        }

        return DocumentProfile(
            document_type=doc_type,
            confidence=confidence,
            features=features,
            metadata=metadata,
            suggested_chunk_size=chunk_size
        )

    def _extract_features(self, text: str) -> Dict[str, any]:
        """Extract structural and content features from text."""
        lines = text.split('\n')
        total_lines = len(lines)

        features = {
            # Structural features
            'avg_line_length': sum(len(line) for line in lines) / max(total_lines, 1),
            'short_line_ratio': sum(1 for line in lines if len(line.strip()) < 50) / max(total_lines, 1),
            'table_density': self._calculate_table_density(text),
            'caps_density': self._calculate_caps_density(text),

            # Content patterns
            'reference_signals': self._count_patterns(text, self.reference_patterns),
            'administrative_signals': self._count_patterns(text, self.administrative_patterns),
            'report_signals': self._count_patterns(text, self.government_report_patterns),

            # Colonial discourse markers
            'colonial_markers': self._detect_colonial_discourse(text),

            # Structural markers
            'has_alphabetical_entries': self._detect_alphabetical_entries(text),
            'has_roman_numerals': bool(re.search(r'^\s*[IVX]+\.—', text, re.MULTILINE)),
            'has_monetary_figures': bool(re.search(r'[\£\$]\s*\d+', text)),
        }

        return features

    def _calculate_table_density(self, text: str) -> float:
        """Calculate the density of table-like structures."""
        lines = text.split('\n')
        table_lines = sum(1 for line in lines if '|' in line or '\t' in line)
        return table_lines / max(len(lines), 1)

    def _calculate_caps_density(self, text: str) -> float:
        """Calculate density of all-caps words (common in reference works)."""
        words = text.split()
        caps_words = sum(1 for word in words if word.isupper() and len(word) > 2)
        return caps_words / max(len(words), 1)

    def _count_patterns(self, text: str, patterns: List[str]) -> int:
        """Count matches for a list of regex patterns."""
        total_matches = 0
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            total_matches += len(matches)
        return total_matches

    def _detect_alphabetical_entries(self, text: str) -> bool:
        """Detect if document has alphabetical entry structure."""
        # Look for patterns like "WORD, definition..." followed by next alphabetical entry
        pattern = r'^[A-Z]{2,}[A-Z\s]*[A-Z]\s*,'
        matches = re.findall(pattern, text, re.MULTILINE)
        return len(matches) > 5  # Need multiple entries to be confident

    def _detect_colonial_discourse(self, text: str) -> List[str]:
        """Detect colonial discourse markers for bias flagging."""
        colonial_markers = []

        patterns = {
            'administrative_colonial': [
                r'Colonial\s+Office', r'Governor\s+and\s+Commander',
                r'Her\s+Majesty[\'\u2019]?s\s+Government', r'British\s+Empire'
            ],
            'hierarchical_language': [
                r'native\s+administration', r'tribal\s+authority',
                r'barbarous\s+customs', r'civiliz[ei]ng\s+mission'
            ],
            'territorial_control': [
                r'Protectorate', r'Crown\s+Colony', r'Dependencies',
                r'British\s+jurisdiction'
            ]
        }

        for category, pattern_list in patterns.items():
            for pattern in pattern_list:
                if re.search(pattern, text, re.IGNORECASE):
                    colonial_markers.append(f"{category}: {pattern}")

        return colonial_markers

    def _classify_document(self, text: str, features: Dict) -> Tuple[DocumentType, float]:
        """Classify document type based on features."""
        scores = {
            DocumentType.REFERENCE: 0.0,
            DocumentType.ADMINISTRATIVE: 0.0,
            DocumentType.GOVERNMENT_REPORT: 0.0,
            DocumentType.NARRATIVE: 0.0,
            DocumentType.LEGAL: 0.0,
        }

        # Reference work scoring
        if features['has_alphabetical_entries']:
            scores[DocumentType.REFERENCE] += 0.4
        if features['caps_density'] > 0.05:
            scores[DocumentType.REFERENCE] += 0.2
        if features['reference_signals'] > 10:
            scores[DocumentType.REFERENCE] += 0.3

        # Administrative document scoring
        if features['administrative_signals'] > 5:
            scores[DocumentType.ADMINISTRATIVE] += 0.3
        if features['table_density'] > 0.1:
            scores[DocumentType.ADMINISTRATIVE] += 0.2
        if features['has_monetary_figures']:
            scores[DocumentType.ADMINISTRATIVE] += 0.2
        if len(features['colonial_markers']) > 3:
            scores[DocumentType.ADMINISTRATIVE] += 0.2

        # Government report scoring
        if features['report_signals'] > 3:
            scores[DocumentType.GOVERNMENT_REPORT] += 0.4
        if features['has_roman_numerals']:
            scores[DocumentType.GOVERNMENT_REPORT] += 0.2
        if features['has_monetary_figures'] and features['table_density'] > 0.05:
            scores[DocumentType.GOVERNMENT_REPORT] += 0.2

        # Find best match
        best_type = max(scores.keys(), key=lambda k: scores[k])
        confidence = scores[best_type]

        # If confidence is too low, mark as hybrid
        if confidence < 0.3:
            return DocumentType.HYBRID, confidence

        return best_type, confidence

    def _suggest_chunk_size(self, doc_type: DocumentType, features: Dict) -> Tuple[int, int]:
        """Suggest appropriate chunk size range based on document type."""
        size_ranges = {
            DocumentType.REFERENCE: (400, 800),      # Complete entries
            DocumentType.ADMINISTRATIVE: (800, 1200), # Complete records/sections
            DocumentType.GOVERNMENT_REPORT: (600, 1000), # Logical sections
            DocumentType.NARRATIVE: (800, 1200),     # Story segments
            DocumentType.LEGAL: (600, 1000),         # Legal clauses
            DocumentType.HYBRID: (600, 1000),        # Conservative default
        }

        base_min, base_max = size_ranges[doc_type]

        # Adjust based on features
        if features['table_density'] > 0.1:
            # Increase size to preserve table integrity
            base_min = int(base_min * 1.2)
            base_max = int(base_max * 1.2)

        if features['avg_line_length'] < 40:
            # Shorter lines suggest need for larger chunks
            base_min = int(base_min * 1.1)
            base_max = int(base_max * 1.1)

        return (base_min, base_max)