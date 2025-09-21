#!/usr/bin/env python3
"""
Side-by-side comparison of chunking strategies on historical OCR documents
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
import statistics

@dataclass
class Chunk:
    """Represents a text chunk with metadata"""
    id: str
    text: str
    start_pos: int
    end_pos: int
    strategy: str
    metadata: Dict[str, Any]

class ChunkingStrategy:
    """Base class for chunking strategies"""

    def __init__(self, name: str):
        self.name = name

    def chunk(self, text: str, doc_id: str) -> List[Chunk]:
        raise NotImplementedError

class OverlappingChunker(ChunkingStrategy):
    """Simple overlapping text chunks (baseline)"""

    def __init__(self, chunk_size: int = 800, overlap: int = 200):
        super().__init__(f"overlapping_{chunk_size}_{overlap}")
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str, doc_id: str) -> List[Chunk]:
        chunks = []
        start = 0
        chunk_id = 0

        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunk_text = text[start:end]

            # Try to break at sentence boundary if possible
            if end < len(text):
                last_period = chunk_text.rfind('.')
                if last_period > self.chunk_size * 0.7:
                    end = start + last_period + 1
                    chunk_text = text[start:end]

            chunks.append(Chunk(
                id=f"{doc_id}_{self.name}_{chunk_id}",
                text=chunk_text.strip(),
                start_pos=start,
                end_pos=end,
                strategy=self.name,
                metadata={"length": len(chunk_text.strip())}
            ))

            start = end - self.overlap
            chunk_id += 1

            if start >= len(text):
                break

        return chunks

class StructureAwareChunker(ChunkingStrategy):
    """Chunks based on document structure (paragraphs, tables, sections)"""

    def __init__(self):
        super().__init__("structure_aware")

    def chunk(self, text: str, doc_id: str) -> List[Chunk]:
        chunks = []
        chunk_id = 0

        # Split by major structural breaks first
        sections = self._split_by_structure(text)

        for section_start, section_text, section_type in sections:
            # Further split if section is too large
            if len(section_text) > 1500:
                subsections = self._split_large_section(section_text, section_type)
                for i, subsection in enumerate(subsections):
                    chunks.append(Chunk(
                        id=f"{doc_id}_{self.name}_{chunk_id}",
                        text=subsection.strip(),
                        start_pos=section_start,
                        end_pos=section_start + len(subsection),
                        strategy=self.name,
                        metadata={
                            "type": section_type,
                            "subsection": i,
                            "length": len(subsection.strip())
                        }
                    ))
                    chunk_id += 1
            else:
                chunks.append(Chunk(
                    id=f"{doc_id}_{self.name}_{chunk_id}",
                    text=section_text.strip(),
                    start_pos=section_start,
                    end_pos=section_start + len(section_text),
                    strategy=self.name,
                    metadata={
                        "type": section_type,
                        "length": len(section_text.strip())
                    }
                ))
                chunk_id += 1

        return chunks

    def _split_by_structure(self, text: str) -> List[Tuple[int, str, str]]:
        """Split text by structural elements"""
        sections = []
        lines = text.split('\n')
        current_section = []
        current_type = "text"
        current_start = 0
        pos = 0

        for line in lines:
            line_len = len(line) + 1  # +1 for newline

            # Detect section type
            if self._is_table_line(line):
                if current_type != "table":
                    # Save previous section
                    if current_section:
                        sections.append((current_start, '\n'.join(current_section), current_type))
                    current_section = [line]
                    current_type = "table"
                    current_start = pos
                else:
                    current_section.append(line)

            elif self._is_header(line):
                # Headers start new sections
                if current_section:
                    sections.append((current_start, '\n'.join(current_section), current_type))
                current_section = [line]
                current_type = "header"
                current_start = pos

            elif line.strip() == "":
                # Empty lines might indicate section breaks
                if current_section:
                    current_section.append(line)

            else:
                # Regular text
                if current_type != "text" and current_type != "header":
                    # Save previous section
                    if current_section:
                        sections.append((current_start, '\n'.join(current_section), current_type))
                    current_section = [line]
                    current_type = "text"
                    current_start = pos
                else:
                    current_section.append(line)
                    if current_type == "header":
                        current_type = "text"  # Header + text becomes text section

            pos += line_len

        # Add final section
        if current_section:
            sections.append((current_start, '\n'.join(current_section), current_type))

        return sections

    def _is_table_line(self, line: str) -> bool:
        """Check if line is part of a table"""
        return '|' in line and line.count('|') >= 2

    def _is_header(self, line: str) -> bool:
        """Check if line is a header"""
        stripped = line.strip()
        return (len(stripped) > 5 and
                (stripped.isupper() or
                 re.match(r'^[A-Z][A-Za-z\s\-]{5,}\.?\s*$', stripped) or
                 re.match(r'^(CHAPTER|PART|SECTION)\s+[IVX\d]+', stripped, re.IGNORECASE)))

    def _split_large_section(self, text: str, section_type: str) -> List[str]:
        """Split large sections into smaller chunks"""
        if section_type == "table":
            # Split table by groups of rows
            lines = text.split('\n')
            chunks = []
            current_chunk = []

            for line in lines:
                current_chunk.append(line)
                if len('\n'.join(current_chunk)) > 1200:
                    chunks.append('\n'.join(current_chunk))
                    current_chunk = []

            if current_chunk:
                chunks.append('\n'.join(current_chunk))

            return chunks

        else:
            # Split text by paragraphs
            paragraphs = text.split('\n\n')
            chunks = []
            current_chunk = []

            for para in paragraphs:
                current_chunk.append(para)
                if len('\n\n'.join(current_chunk)) > 1200:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []

            if current_chunk:
                chunks.append('\n\n'.join(current_chunk))

            return chunks

class ParagraphChunker(ChunkingStrategy):
    """Chunks based on paragraph boundaries"""

    def __init__(self, max_paragraphs: int = 3):
        super().__init__(f"paragraph_{max_paragraphs}")
        self.max_paragraphs = max_paragraphs

    def chunk(self, text: str, doc_id: str) -> List[Chunk]:
        chunks = []
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

        chunk_id = 0
        current_pos = 0

        for i in range(0, len(paragraphs), self.max_paragraphs):
            chunk_paragraphs = paragraphs[i:i + self.max_paragraphs]
            chunk_text = '\n\n'.join(chunk_paragraphs)

            chunks.append(Chunk(
                id=f"{doc_id}_{self.name}_{chunk_id}",
                text=chunk_text,
                start_pos=current_pos,
                end_pos=current_pos + len(chunk_text),
                strategy=self.name,
                metadata={
                    "paragraph_count": len(chunk_paragraphs),
                    "length": len(chunk_text)
                }
            ))

            current_pos += len(chunk_text) + 2  # +2 for paragraph separator
            chunk_id += 1

        return chunks

class ChunkingComparator:
    """Compare different chunking strategies on test documents"""

    def __init__(self):
        self.strategies = [
            OverlappingChunker(chunk_size=600, overlap=150),
            OverlappingChunker(chunk_size=1000, overlap=200),
            ParagraphChunker(max_paragraphs=2),
            ParagraphChunker(max_paragraphs=4),
            StructureAwareChunker()
        ]

    def compare_strategies(self, test_dir: Path) -> Dict[str, Any]:
        """Compare all strategies on test documents"""
        results = {}

        for json_file in test_dir.glob("*.json"):
            print(f"\nProcessing {json_file.name}...")

            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            text = data['text']
            doc_id = json_file.stem

            file_results = {
                'document': json_file.name,
                'text_length': len(text),
                'pages': data.get('metadata', {}).get('pdf-total-pages', 1),
                'strategies': {}
            }

            for strategy in self.strategies:
                chunks = strategy.chunk(text, doc_id)

                strategy_stats = self._analyze_chunks(chunks)
                file_results['strategies'][strategy.name] = strategy_stats

                print(f"  {strategy.name}: {len(chunks)} chunks, "
                      f"avg {strategy_stats['avg_length']:.0f} chars")

            results[doc_id] = file_results

        return results

    def _analyze_chunks(self, chunks: List[Chunk]) -> Dict[str, Any]:
        """Analyze chunk characteristics"""
        if not chunks:
            return {}

        lengths = [len(chunk.text) for chunk in chunks]

        return {
            'count': len(chunks),
            'avg_length': statistics.mean(lengths),
            'min_length': min(lengths),
            'max_length': max(lengths),
            'std_length': statistics.stdev(lengths) if len(lengths) > 1 else 0,
            'total_chars': sum(lengths),
            'chunks_under_300': sum(1 for l in lengths if l < 300),
            'chunks_over_1500': sum(1 for l in lengths if l > 1500)
        }

    def print_summary(self, results: Dict[str, Any]):
        """Print comparison summary"""
        print("\n" + "="*60)
        print("CHUNKING STRATEGY COMPARISON SUMMARY")
        print("="*60)

        # Overall statistics by strategy
        strategy_totals = {}

        for doc_results in results.values():
            for strategy_name, stats in doc_results['strategies'].items():
                if strategy_name not in strategy_totals:
                    strategy_totals[strategy_name] = []
                strategy_totals[strategy_name].append(stats)

        print(f"\n{'Strategy':<25} {'Avg Chunks':<12} {'Avg Length':<12} {'Consistency':<12}")
        print("-" * 60)

        for strategy_name, stats_list in strategy_totals.items():
            avg_chunks = statistics.mean([s['count'] for s in stats_list])
            avg_length = statistics.mean([s['avg_length'] for s in stats_list])

            # Consistency measure (lower std deviation is more consistent)
            length_stds = [s['std_length'] for s in stats_list if s['std_length'] > 0]
            consistency = statistics.mean(length_stds) if length_stds else 0

            print(f"{strategy_name:<25} {avg_chunks:<12.1f} {avg_length:<12.0f} {consistency:<12.0f}")

        # Document-specific observations
        print(f"\n{'Document':<20} {'Pages':<8} {'Text Length':<12} {'Best Strategy':<20}")
        print("-" * 60)

        for doc_id, doc_results in results.items():
            pages = doc_results['pages']
            text_len = doc_results['text_length']

            # Find strategy with most consistent chunk sizes
            best_strategy = min(doc_results['strategies'].items(),
                              key=lambda x: x[1]['std_length'] if x[1]['std_length'] > 0 else float('inf'))

            print(f"{doc_results['document']:<20} {pages:<8} {text_len:<12,} {best_strategy[0]:<20}")

def main():
    """Run chunking strategy comparison"""
    import sys
    if len(sys.argv) > 1:
        test_dir = Path(sys.argv[1])
    else:
        test_dir = Path("data/test_subset")

    print(f"Looking for files in: {test_dir.absolute()}")
    files = list(test_dir.glob("*.json"))
    print(f"Found {len(files)} JSON files")

    comparator = ChunkingComparator()

    print("Starting chunking strategy comparison...")
    results = comparator.compare_strategies(test_dir)
    comparator.print_summary(results)

    # Save detailed results
    output_file = "chunking_comparison_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)

    print(f"\nDetailed results saved to {output_file}")

if __name__ == "__main__":
    main()