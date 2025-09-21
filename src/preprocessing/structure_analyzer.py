#!/usr/bin/env python3
"""
Structure-aware text analysis for OLM-OCR JSON files
Alternative to DocLing for historical documents
"""

import json
import re
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from pathlib import Path

@dataclass
class TextSegment:
    """Represents a structured segment of text"""
    content: str
    segment_type: str  # 'header', 'paragraph', 'table', 'list', 'page_break'
    start_pos: int
    end_pos: int
    confidence: float
    metadata: Dict[str, Any]

class StructureAnalyzer:
    """Analyzes text structure from OLM-OCR processed documents"""

    def __init__(self):
        # Patterns for different structural elements
        self.patterns = {
            'title': re.compile(r'^[A-Z\s]{10,}$', re.MULTILINE),
            'header': re.compile(r'^[A-Z][A-Za-z\s\-]{5,}\.?\s*$', re.MULTILINE),
            'table_row': re.compile(r'.*\|.*\|.*'),
            'list_item': re.compile(r'^\s*[-*•]\s+', re.MULTILINE),
            'numbered_list': re.compile(r'^\s*\d+[\.\)]\s+', re.MULTILINE),
            'page_break': re.compile(r'\n\s*\n\s*\n'),
            'section_break': re.compile(r'\n\s*\n'),
            'chapter_header': re.compile(r'^(CHAPTER|PART|SECTION)\s+[IVX\d]+', re.MULTILINE | re.IGNORECASE),
            'date_header': re.compile(r'^\s*(JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\s*,?\s*\d{4}', re.MULTILINE | re.IGNORECASE)
        }

    def analyze_structure(self, text: str, metadata: Dict[str, Any] = None) -> List[TextSegment]:
        """Analyze the structure of extracted text"""
        segments = []
        lines = text.split('\n')
        current_pos = 0

        # Detect major structural elements
        table_sections = self._find_table_sections(text)
        headers = self._find_headers(text)
        page_breaks = self._find_page_breaks(text)

        # Process line by line
        i = 0
        while i < len(lines):
            line = lines[i]
            line_start = current_pos
            line_end = current_pos + len(line)

            # Skip empty lines
            if not line.strip():
                current_pos = line_end + 1  # +1 for newline
                i += 1
                continue

            segment = self._classify_line(line, line_start, line_end, i, lines)
            if segment:
                segments.append(segment)

            current_pos = line_end + 1  # +1 for newline
            i += 1

        # Post-process to merge related segments
        segments = self._merge_related_segments(segments)

        return segments

    def _find_table_sections(self, text: str) -> List[Tuple[int, int]]:
        """Find sections that contain tables"""
        table_sections = []
        lines = text.split('\n')
        table_start = None

        for i, line in enumerate(lines):
            if self.patterns['table_row'].match(line):
                if table_start is None:
                    table_start = i
            elif table_start is not None:
                # End of table section
                table_sections.append((table_start, i))
                table_start = None

        if table_start is not None:
            table_sections.append((table_start, len(lines)))

        return table_sections

    def _find_headers(self, text: str) -> List[Tuple[int, str, str]]:
        """Find headers in the text"""
        headers = []

        # Find various types of headers
        for pattern_name, pattern in [
            ('title', self.patterns['title']),
            ('chapter', self.patterns['chapter_header']),
            ('date', self.patterns['date_header']),
            ('header', self.patterns['header'])
        ]:
            for match in pattern.finditer(text):
                headers.append((match.start(), match.group(), pattern_name))

        return sorted(headers, key=lambda x: x[0])

    def _find_page_breaks(self, text: str) -> List[int]:
        """Find likely page breaks"""
        page_breaks = []
        for match in self.patterns['page_break'].finditer(text):
            page_breaks.append(match.start())
        return page_breaks

    def _classify_line(self, line: str, start_pos: int, end_pos: int,
                      line_num: int, all_lines: List[str]) -> TextSegment:
        """Classify a single line of text"""

        line_stripped = line.strip()

        # Check for different types of content
        if self.patterns['title'].match(line_stripped):
            return TextSegment(
                content=line_stripped,
                segment_type='title',
                start_pos=start_pos,
                end_pos=end_pos,
                confidence=0.9,
                metadata={'line_num': line_num}
            )

        elif self.patterns['chapter_header'].match(line_stripped):
            return TextSegment(
                content=line_stripped,
                segment_type='chapter_header',
                start_pos=start_pos,
                end_pos=end_pos,
                confidence=0.95,
                metadata={'line_num': line_num}
            )

        elif self.patterns['date_header'].match(line_stripped):
            return TextSegment(
                content=line_stripped,
                segment_type='date_header',
                start_pos=start_pos,
                end_pos=end_pos,
                confidence=0.9,
                metadata={'line_num': line_num}
            )

        elif self.patterns['table_row'].match(line_stripped):
            return TextSegment(
                content=line_stripped,
                segment_type='table_row',
                start_pos=start_pos,
                end_pos=end_pos,
                confidence=0.8,
                metadata={'line_num': line_num, 'columns': line_stripped.count('|') + 1}
            )

        elif self.patterns['list_item'].match(line_stripped):
            return TextSegment(
                content=line_stripped,
                segment_type='list_item',
                start_pos=start_pos,
                end_pos=end_pos,
                confidence=0.8,
                metadata={'line_num': line_num}
            )

        elif self.patterns['numbered_list'].match(line_stripped):
            return TextSegment(
                content=line_stripped,
                segment_type='numbered_list',
                start_pos=start_pos,
                end_pos=end_pos,
                confidence=0.8,
                metadata={'line_num': line_num}
            )

        elif len(line_stripped) > 50 and not line_stripped.isupper():
            return TextSegment(
                content=line_stripped,
                segment_type='paragraph',
                start_pos=start_pos,
                end_pos=end_pos,
                confidence=0.7,
                metadata={'line_num': line_num, 'length': len(line_stripped)}
            )

        else:
            return TextSegment(
                content=line_stripped,
                segment_type='other',
                start_pos=start_pos,
                end_pos=end_pos,
                confidence=0.5,
                metadata={'line_num': line_num}
            )

    def _merge_related_segments(self, segments: List[TextSegment]) -> List[TextSegment]:
        """Merge related segments like consecutive paragraphs or table rows"""
        if not segments:
            return segments

        merged = []
        current_group = [segments[0]]

        for segment in segments[1:]:
            # Merge consecutive paragraphs
            if (current_group[-1].segment_type == 'paragraph' and
                segment.segment_type == 'paragraph' and
                segment.start_pos - current_group[-1].end_pos < 50):
                current_group.append(segment)

            # Merge consecutive table rows
            elif (current_group[-1].segment_type == 'table_row' and
                  segment.segment_type == 'table_row'):
                current_group.append(segment)

            else:
                # End current group, start new one
                merged.append(self._create_merged_segment(current_group))
                current_group = [segment]

        # Add the last group
        merged.append(self._create_merged_segment(current_group))

        return merged

    def _create_merged_segment(self, segments: List[TextSegment]) -> TextSegment:
        """Create a merged segment from a group of related segments"""
        if len(segments) == 1:
            return segments[0]

        # Merge multiple segments
        content = '\n'.join(seg.content for seg in segments)
        segment_type = segments[0].segment_type
        if segment_type == 'table_row':
            segment_type = 'table'
        elif segment_type == 'paragraph':
            segment_type = 'text_block'

        return TextSegment(
            content=content,
            segment_type=segment_type,
            start_pos=segments[0].start_pos,
            end_pos=segments[-1].end_pos,
            confidence=sum(seg.confidence for seg in segments) / len(segments),
            metadata={
                'merged_count': len(segments),
                'original_types': [seg.segment_type for seg in segments]
            }
        )

    def get_structure_summary(self, segments: List[TextSegment]) -> Dict[str, Any]:
        """Get a summary of the document structure"""
        type_counts = {}
        total_length = 0

        for segment in segments:
            type_counts[segment.segment_type] = type_counts.get(segment.segment_type, 0) + 1
            total_length += len(segment.content)

        return {
            'total_segments': len(segments),
            'total_length': total_length,
            'segment_types': type_counts,
            'avg_segment_length': total_length / len(segments) if segments else 0,
            'structure_complexity': len(type_counts)
        }

def main():
    """Test the structure analyzer on our test files"""
    analyzer = StructureAnalyzer()
    test_dir = Path("data/test_subset")

    for json_file in test_dir.glob("*.json"):
        if json_file.name.endswith('.json'):
            print(f"\n=== Analyzing {json_file.name} ===")

            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            text = data['text']
            metadata = data.get('metadata', {})

            # Analyze structure
            segments = analyzer.analyze_structure(text, metadata)
            summary = analyzer.get_structure_summary(segments)

            print(f"Document: {json_file.name}")
            print(f"Pages: {metadata.get('pdf-total-pages', 1)}")
            print(f"Total segments: {summary['total_segments']}")
            print(f"Segment types: {summary['segment_types']}")
            print(f"Average segment length: {summary['avg_segment_length']:.0f} chars")
            print(f"Structure complexity: {summary['structure_complexity']}")

            # Show first few segments
            print("\nFirst 3 segments:")
            for i, segment in enumerate(segments[:3]):
                print(f"  {i+1}. [{segment.segment_type}] {segment.content[:100]}...")

if __name__ == "__main__":
    main()