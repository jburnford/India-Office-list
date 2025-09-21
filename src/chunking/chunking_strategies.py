"""
Adaptive Chunking Strategies - Specialized chunkers for different document types.

This module implements document-type-specific chunking strategies as described
in the adaptive chunking framework. Each strategy is optimized for the unique
structural and semantic characteristics of its target document type.
"""

import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod

@dataclass
class Chunk:
    """Represents a text chunk with metadata."""
    text: str
    start_pos: int
    end_pos: int
    chunk_id: str
    metadata: Dict[str, any]

class BaseChunker(ABC):
    """Base class for all chunking strategies."""

    def __init__(self, min_size: int = 600, max_size: int = 1000):
        self.min_size = min_size
        self.max_size = max_size

    @abstractmethod
    def chunk(self, text: str, document_id: str = "unknown") -> List[Chunk]:
        """Chunk text according to strategy-specific rules."""
        pass

    def _create_chunk(self, text: str, start: int, end: int,
                     chunk_id: str, metadata: Dict = None) -> Chunk:
        """Helper to create a chunk with default metadata."""
        if metadata is None:
            metadata = {}

        return Chunk(
            text=text[start:end].strip(),
            start_pos=start,
            end_pos=end,
            chunk_id=chunk_id,
            metadata={
                'size': end - start,
                'strategy': self.__class__.__name__,
                **metadata
            }
        )

class ReferenceChunker(BaseChunker):
    """
    Chunker for reference works like Encyclopædia Britannica.

    Preserves entry boundaries and cross-references.
    Handles alphabetical organization and nested definitions.
    """

    def __init__(self, min_size: int = 400, max_size: int = 800):
        super().__init__(min_size, max_size)

        # Patterns for detecting entry boundaries
        self.entry_patterns = [
            r'^[A-Z]{2,}[A-Z\s]*[A-Z]\s*,',  # Main entries: "CABINET,"
            r'^[A-Z][A-Z\s]+[A-Z]\s*\.',     # Variant entries: "CABLE."
            r'^[A-Z]+\s*\(',                 # Parenthetical entries: "CABO ("
        ]

    def chunk(self, text: str, document_id: str = "unknown") -> List[Chunk]:
        """Chunk reference work by detecting entry boundaries."""
        chunks = []
        lines = text.split('\n')

        current_chunk_start = 0
        current_chunk_lines = []
        entry_count = 0

        for i, line in enumerate(lines):
            is_new_entry = self._is_entry_boundary(line)

            # If we hit a new entry and have accumulated content
            if is_new_entry and current_chunk_lines:
                # Check if we should finalize current chunk
                current_text = '\n'.join(current_chunk_lines)

                if (len(current_text) >= self.min_size or
                    entry_count >= 3):  # At least 3 entries or min size

                    # Create chunk
                    chunk_end = current_chunk_start + len(current_text)
                    chunk_id = f"{document_id}_ref_{len(chunks)}"

                    metadata = {
                        'entry_count': entry_count,
                        'type': 'reference_entry_group',
                        'cross_references': self._extract_cross_references(current_text)
                    }

                    chunks.append(self._create_chunk(
                        text, current_chunk_start, chunk_end, chunk_id, metadata
                    ))

                    # Start new chunk
                    current_chunk_start = chunk_end
                    current_chunk_lines = []
                    entry_count = 0

            current_chunk_lines.append(line)
            if is_new_entry:
                entry_count += 1

            # Handle oversized chunks
            current_text = '\n'.join(current_chunk_lines)
            if len(current_text) > self.max_size:
                # Force split at reasonable boundary
                self._force_split_chunk(chunks, current_chunk_lines,
                                      current_chunk_start, document_id)

                # Reset for next chunk
                current_chunk_start += len(current_text)
                current_chunk_lines = []
                entry_count = 0

        # Handle final chunk
        if current_chunk_lines:
            current_text = '\n'.join(current_chunk_lines)
            chunk_end = current_chunk_start + len(current_text)
            chunk_id = f"{document_id}_ref_{len(chunks)}"

            metadata = {
                'entry_count': entry_count,
                'type': 'reference_entry_group',
                'cross_references': self._extract_cross_references(current_text)
            }

            chunks.append(self._create_chunk(
                text, current_chunk_start, chunk_end, chunk_id, metadata
            ))

        return chunks

    def _is_entry_boundary(self, line: str) -> bool:
        """Detect if line starts a new encyclopedia entry."""
        line = line.strip()
        if not line:
            return False

        for pattern in self.entry_patterns:
            if re.match(pattern, line):
                return True
        return False

    def _extract_cross_references(self, text: str) -> List[str]:
        """Extract cross-references like 'See CABINET' from text."""
        refs = []
        patterns = [
            r'\b(?:See|see)\s+([A-Z][A-Za-z]+)\b',
            r'\b(?:See also|see also)\s+([A-Z][A-Za-z]+)\b'
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text)
            refs.extend(matches)

        return list(set(refs))  # Remove duplicates

    def _force_split_chunk(self, chunks: List[Chunk], lines: List[str],
                          start_pos: int, document_id: str):
        """Force split oversized chunk at best available boundary."""
        # Find best split point (prefer after complete entries)
        split_point = len(lines) // 2

        # Look for entry boundary near midpoint
        for i in range(max(0, split_point - 5), min(len(lines), split_point + 5)):
            if i < len(lines) and self._is_entry_boundary(lines[i]):
                split_point = i
                break

        # Create first chunk
        first_chunk_lines = lines[:split_point]
        first_text = '\n'.join(first_chunk_lines)
        chunk_id = f"{document_id}_ref_{len(chunks)}"

        chunk = Chunk(
            text=first_text,
            start_pos=start_pos,
            end_pos=start_pos + len(first_text),
            chunk_id=chunk_id,
            metadata={
                'size': len(first_text),
                'strategy': 'ReferenceChunker',
                'type': 'reference_split_chunk'
            }
        )
        chunks.append(chunk)


class AdministrativeChunker(BaseChunker):
    """
    Chunker for administrative documents like Colonial Office Lists.

    Preserves table integrity and departmental boundaries.
    Flags colonial administrative perspectives.
    """

    def __init__(self, min_size: int = 800, max_size: int = 1200):
        super().__init__(min_size, max_size)

    def chunk(self, text: str, document_id: str = "unknown") -> List[Chunk]:
        """Chunk administrative document preserving structural integrity."""
        chunks = []

        # First, identify major structural boundaries
        sections = self._identify_sections(text)

        for section in sections:
            section_chunks = self._chunk_section(section, document_id, len(chunks))
            chunks.extend(section_chunks)

        return chunks

    def _identify_sections(self, text: str) -> List[Dict]:
        """Identify major sections in administrative document."""
        sections = []
        lines = text.split('\n')

        current_section = {
            'start': 0,
            'lines': [],
            'type': 'unknown',
            'has_tables': False
        }

        for i, line in enumerate(lines):
            line_type = self._classify_line(line)

            # Detect section boundaries - only split on significant headings with enough content
            if (line_type in ['major_heading', 'department_header'] and
                current_section['lines'] and
                len('\n'.join(current_section['lines'])) > 100):  # Minimum section size

                # Finalize current section
                current_section['text'] = '\n'.join(current_section['lines'])
                sections.append(current_section)

                # Start new section
                current_section = {
                    'start': i,
                    'lines': [line],
                    'type': line_type,
                    'has_tables': False
                }
            else:
                current_section['lines'].append(line)
                if line_type == 'table_row':
                    current_section['has_tables'] = True

        # Add final section
        if current_section['lines']:
            current_section['text'] = '\n'.join(current_section['lines'])
            sections.append(current_section)

        return sections

    def _classify_line(self, line: str) -> str:
        """Classify line type for administrative document structure."""
        line = line.strip()

        if not line:
            return 'empty'

        # Major headings (all caps, centered-ish)
        if (line.isupper() and len(line) > 10 and
            not line.startswith('|') and '£' not in line):
            return 'major_heading'

        # Department headers
        if re.match(r'^[A-Z][A-Za-z\s]+Department', line):
            return 'department_header'

        # Table rows
        if '|' in line or '\t' in line:
            return 'table_row'

        # Personnel entries (Name, Title pattern)
        if re.match(r'^[A-Z][a-z]+,?\s+[A-Z]', line):
            return 'personnel_entry'

        return 'content'

    def _chunk_section(self, section: Dict, document_id: str,
                      chunk_offset: int) -> List[Chunk]:
        """Chunk a single administrative section."""
        chunks = []
        text = section['text']

        if len(text) <= self.max_size:
            # Section fits in one chunk
            chunk_id = f"{document_id}_admin_{chunk_offset}"
            metadata = {
                'section_type': section['type'],
                'has_tables': section['has_tables'],
                'colonial_discourse_markers': self._detect_colonial_markers(text)
            }

            chunk = Chunk(
                text=text,
                start_pos=0,
                end_pos=len(text),
                chunk_id=chunk_id,
                metadata={
                    'size': len(text),
                    'strategy': 'AdministrativeChunker',
                    **metadata
                }
            )
            chunks.append(chunk)
        else:
            # Need to split section
            chunks.extend(self._split_large_section(section, document_id, chunk_offset))

        return chunks

    def _split_large_section(self, section: Dict, document_id: str,
                           chunk_offset: int) -> List[Chunk]:
        """Split large administrative section preserving table integrity."""
        chunks = []
        lines = section['text'].split('\n')

        current_chunk_lines = []
        in_table = False
        table_buffer = []

        for line in lines:
            line_type = self._classify_line(line)

            # Handle table preservation
            if line_type == 'table_row':
                if not in_table:
                    in_table = True
                table_buffer.append(line)
            else:
                if in_table:
                    # End of table - add complete table to chunk
                    current_chunk_lines.extend(table_buffer)
                    table_buffer = []
                    in_table = False

                current_chunk_lines.append(line)

            # Check if chunk is getting too large (but preserve table integrity)
            current_text = '\n'.join(current_chunk_lines)
            if len(current_text) > self.max_size and not in_table:
                # Create chunk
                chunk_id = f"{document_id}_admin_{chunk_offset + len(chunks)}"
                metadata = {
                    'section_type': section['type'],
                    'has_tables': any('|' in l or '\t' in l for l in current_chunk_lines),
                    'colonial_discourse_markers': self._detect_colonial_markers(current_text)
                }

                chunk = Chunk(
                    text=current_text,
                    start_pos=0,
                    end_pos=len(current_text),
                    chunk_id=chunk_id,
                    metadata={
                        'size': len(current_text),
                        'strategy': 'AdministrativeChunker',
                        **metadata
                    }
                )
                chunks.append(chunk)

                current_chunk_lines = []

        # Handle remaining content
        if current_chunk_lines or table_buffer:
            all_remaining = current_chunk_lines + table_buffer
            current_text = '\n'.join(all_remaining)

            chunk_id = f"{document_id}_admin_{chunk_offset + len(chunks)}"
            metadata = {
                'section_type': section['type'],
                'has_tables': any('|' in l or '\t' in l for l in all_remaining),
                'colonial_discourse_markers': self._detect_colonial_markers(current_text)
            }

            chunk = Chunk(
                text=current_text,
                start_pos=0,
                end_pos=len(current_text),
                chunk_id=chunk_id,
                metadata={
                    'size': len(current_text),
                    'strategy': 'AdministrativeChunker',
                    **metadata
                }
            )
            chunks.append(chunk)

        return chunks

    def _detect_colonial_markers(self, text: str) -> List[str]:
        """Detect colonial administrative discourse markers."""
        markers = []

        patterns = {
            'administrative_hierarchy': [
                r'Colonial\s+Office', r'Governor\s+and\s+Commander',
                r'Secretary\s+of\s+State', r'Her\s+Majesty[\'\u2019]?s\s+Government'
            ],
            'territorial_control': [
                r'Crown\s+Colony', r'Protectorate', r'Dependencies',
                r'British\s+jurisdiction', r'native\s+administration'
            ],
            'personnel_titles': [
                r'Commissioner', r'Resident', r'Administrator',
                r'Colonial\s+Secretary', r'Provincial\s+Commissioner'
            ]
        }

        for category, pattern_list in patterns.items():
            for pattern in pattern_list:
                if re.search(pattern, text, re.IGNORECASE):
                    markers.append(f"{category}: {pattern}")

        return markers


class GovernmentReportChunker(BaseChunker):
    """
    Chunker for government reports with mixed narrative and tabular content.

    Preserves narrative flow and maintains table integrity.
    Handles Roman numeral sections and financial data.
    """

    def __init__(self, min_size: int = 600, max_size: int = 1000):
        super().__init__(min_size, max_size)

    def chunk(self, text: str, document_id: str = "unknown") -> List[Chunk]:
        """Chunk government report preserving logical sections."""
        chunks = []

        # Identify major sections by Roman numerals and headings
        sections = self._identify_report_sections(text)

        for section in sections:
            section_chunks = self._chunk_report_section(section, document_id, len(chunks))
            chunks.extend(section_chunks)

        return chunks

    def _identify_report_sections(self, text: str) -> List[Dict]:
        """Identify major sections in government report."""
        sections = []
        lines = text.split('\n')

        current_section = {
            'title': '',
            'lines': [],
            'start_line': 0,
            'has_tables': False,
            'has_financial_data': False
        }

        for i, line in enumerate(lines):
            # Detect section boundaries (Roman numerals, major headings)
            if self._is_section_boundary(line) and current_section['lines']:
                # Finalize current section
                current_section['text'] = '\n'.join(current_section['lines'])
                sections.append(current_section)

                # Start new section
                current_section = {
                    'title': line.strip(),
                    'lines': [line],
                    'start_line': i,
                    'has_tables': False,
                    'has_financial_data': False
                }
            else:
                current_section['lines'].append(line)

                # Track content types
                if '|' in line or '\t' in line:
                    current_section['has_tables'] = True
                if re.search(r'[\£\$]\s*\d+', line):
                    current_section['has_financial_data'] = True

        # Add final section
        if current_section['lines']:
            current_section['text'] = '\n'.join(current_section['lines'])
            sections.append(current_section)

        return sections

    def _is_section_boundary(self, line: str) -> bool:
        """Detect section boundaries in government reports."""
        line = line.strip()

        # Roman numeral sections: "I.—GENERAL"
        if re.match(r'^[IVX]+\.—[A-Z]', line):
            return True

        # Major all-caps headings
        if (line.isupper() and len(line) > 8 and
            not line.startswith('|') and
            not re.search(r'[\£\$]\d', line)):
            return True

        return False

    def _chunk_report_section(self, section: Dict, document_id: str,
                            chunk_offset: int) -> List[Chunk]:
        """Chunk a government report section."""
        chunks = []
        text = section['text']

        if len(text) <= self.max_size:
            # Section fits in one chunk
            chunk_id = f"{document_id}_report_{chunk_offset}"
            metadata = {
                'section_title': section['title'],
                'has_tables': section['has_tables'],
                'has_financial_data': section['has_financial_data'],
                'content_type': self._classify_report_content(text)
            }

            chunk = Chunk(
                text=text,
                start_pos=0,
                end_pos=len(text),
                chunk_id=chunk_id,
                metadata={
                    'size': len(text),
                    'strategy': 'GovernmentReportChunker',
                    **metadata
                }
            )
            chunks.append(chunk)
        else:
            # Split large section at paragraph boundaries
            chunks.extend(self._split_report_section(section, document_id, chunk_offset))

        return chunks

    def _split_report_section(self, section: Dict, document_id: str,
                            chunk_offset: int) -> List[Chunk]:
        """Split large report section at logical boundaries."""
        chunks = []
        paragraphs = section['text'].split('\n\n')

        current_chunk_paras = []

        for para in paragraphs:
            # Check if adding this paragraph would exceed max size
            test_text = '\n\n'.join(current_chunk_paras + [para])

            if len(test_text) > self.max_size and current_chunk_paras:
                # Create chunk with current paragraphs
                current_text = '\n\n'.join(current_chunk_paras)
                chunk_id = f"{document_id}_report_{chunk_offset + len(chunks)}"

                metadata = {
                    'section_title': section['title'],
                    'has_tables': '|' in current_text or '\t' in current_text,
                    'has_financial_data': bool(re.search(r'[\£\$]\s*\d+', current_text)),
                    'content_type': self._classify_report_content(current_text)
                }

                chunk = Chunk(
                    text=current_text,
                    start_pos=0,
                    end_pos=len(current_text),
                    chunk_id=chunk_id,
                    metadata={
                        'size': len(current_text),
                        'strategy': 'GovernmentReportChunker',
                        **metadata
                    }
                )
                chunks.append(chunk)

                current_chunk_paras = [para]
            else:
                current_chunk_paras.append(para)

        # Handle remaining paragraphs
        if current_chunk_paras:
            current_text = '\n\n'.join(current_chunk_paras)
            chunk_id = f"{document_id}_report_{chunk_offset + len(chunks)}"

            metadata = {
                'section_title': section['title'],
                'has_tables': '|' in current_text or '\t' in current_text,
                'has_financial_data': bool(re.search(r'[\£\$]\s*\d+', current_text)),
                'content_type': self._classify_report_content(current_text)
            }

            chunk = Chunk(
                text=current_text,
                start_pos=0,
                end_pos=len(current_text),
                chunk_id=chunk_id,
                metadata={
                    'size': len(current_text),
                    'strategy': 'GovernmentReportChunker',
                    **metadata
                }
            )
            chunks.append(chunk)

        return chunks

    def _classify_report_content(self, text: str) -> str:
        """Classify the type of content in report section."""
        if re.search(r'Revenue|Expenditure|Financial', text, re.IGNORECASE):
            return 'financial'
        elif re.search(r'ADMINISTRATION|ESTABLISHMENT', text, re.IGNORECASE):
            return 'administrative'
        elif '|' in text and re.search(r'\d+', text):
            return 'tabular_data'
        else:
            return 'narrative'


class HybridChunker(BaseChunker):
    """
    Fallback chunker for unknown or mixed document types.

    Uses conservative semantic chunking with sentence boundaries.
    """

    def chunk(self, text: str, document_id: str = "unknown") -> List[Chunk]:
        """Chunk text using sentence-aware splitting."""
        chunks = []
        sentences = self._split_into_sentences(text)

        current_chunk_sentences = []

        for sentence in sentences:
            # Check if adding this sentence would exceed max size
            test_text = ' '.join(current_chunk_sentences + [sentence])

            if len(test_text) > self.max_size and current_chunk_sentences:
                # Create chunk
                current_text = ' '.join(current_chunk_sentences)
                chunk_id = f"{document_id}_hybrid_{len(chunks)}"

                chunk = Chunk(
                    text=current_text,
                    start_pos=0,
                    end_pos=len(current_text),
                    chunk_id=chunk_id,
                    metadata={
                        'size': len(current_text),
                        'strategy': 'HybridChunker',
                        'sentence_count': len(current_chunk_sentences)
                    }
                )
                chunks.append(chunk)

                current_chunk_sentences = [sentence]
            else:
                current_chunk_sentences.append(sentence)

        # Handle remaining sentences
        if current_chunk_sentences:
            current_text = ' '.join(current_chunk_sentences)
            chunk_id = f"{document_id}_hybrid_{len(chunks)}"

            chunk = Chunk(
                text=current_text,
                start_pos=0,
                end_pos=len(current_text),
                chunk_id=chunk_id,
                metadata={
                    'size': len(current_text),
                    'strategy': 'HybridChunker',
                    'sentence_count': len(current_chunk_sentences)
                }
            )
            chunks.append(chunk)

        return chunks

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences, handling abbreviations."""
        # Simple sentence splitting (can be enhanced with NLTK)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]