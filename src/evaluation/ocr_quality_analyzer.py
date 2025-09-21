#!/usr/bin/env python3
"""
Thorough analysis of OLM-OCR structure quality and error patterns
Critical evaluation before building chunking strategies
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple
from collections import Counter
import statistics

class OCRQualityAnalyzer:
    """Analyzes potential OCR errors and structure quality issues"""

    def __init__(self):
        # Common OCR error patterns
        self.error_patterns = {
            'character_substitution': [
                (r'[il1|]{2,}', 'consecutive similar chars (l/1/I/|)'),
                (r'rn', 'potential m substitution'),
                (r'cl', 'potential d substitution'),
                (r'tn', 'potential in substitution'),
                (r'[0O]{2,}', 'consecutive O/0 confusion'),
            ],
            'word_breaks': [
                (r'\b[a-z]{1,2}\s[a-z]{1,2}\b', 'broken words (short fragments)'),
                (r'\b[A-Z]{1}[a-z]+[A-Z]{1}[a-z]+\b', 'mid-word capitals'),
            ],
            'punctuation_errors': [
                (r'[.]{2,}', 'multiple periods'),
                (r'[,]{2,}', 'multiple commas'),
                (r'[;:]{2,}', 'multiple semicolons/colons'),
                (r'\s+[.,:;]', 'floating punctuation'),
            ],
            'spacing_issues': [
                (r'\s{3,}', 'excessive whitespace'),
                (r'[a-zA-Z][.,:;][a-zA-Z]', 'missing spaces around punctuation'),
                (r'\b[a-z]+[A-Z]', 'missing space before capital'),
            ],
            'table_structure': [
                (r'\|\s*\|', 'empty table cells'),
                (r'\|[^|\n]{100,}', 'overly long table cells'),
                (r'^[^|]*\|[^|]*$', 'single column tables'),
            ]
        }

        # Historical text patterns that might be mistaken for errors
        self.historical_patterns = {
            'archaic_spelling': [
                (r'\b\w*[ye]\b', 'archaic endings'),
                (r'\b[A-Z][a-z]*[ſ][a-z]*\b', 'long s character'),
                (r'\b\w*[ae]\b', 'old English endings'),
            ],
            'abbreviations': [
                (r'\b[A-Z]{2,}\b', 'abbreviations'),
                (r'\b[A-Z][a-z]*\.\b', 'abbreviated titles'),
                (r'&c\.', 'et cetera abbreviation'),
            ]
        }

    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """Comprehensive analysis of a single OCR file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        text = data['text']
        metadata = data.get('metadata', {})

        analysis = {
            'file': file_path.name,
            'basic_stats': self._get_basic_stats(text, metadata),
            'error_analysis': self._analyze_errors(text),
            'structure_quality': self._analyze_structure_quality(text),
            'table_analysis': self._analyze_tables(text),
            'readability': self._analyze_readability(text),
            'historical_features': self._analyze_historical_features(text)
        }

        return analysis

    def _get_basic_stats(self, text: str, metadata: Dict) -> Dict[str, Any]:
        """Basic statistics about the text"""
        lines = text.split('\n')
        words = text.split()

        return {
            'total_chars': len(text),
            'total_words': len(words),
            'total_lines': len(lines),
            'pages': metadata.get('pdf-total-pages', 1),
            'avg_line_length': statistics.mean([len(line) for line in lines if line.strip()]),
            'avg_word_length': statistics.mean([len(word) for word in words]),
            'empty_lines': sum(1 for line in lines if not line.strip()),
            'chars_per_page': len(text) / metadata.get('pdf-total-pages', 1)
        }

    def _analyze_errors(self, text: str) -> Dict[str, Any]:
        """Look for potential OCR errors"""
        error_counts = {}

        for category, patterns in self.error_patterns.items():
            category_counts = {}
            for pattern, description in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                category_counts[description] = len(matches)
                if matches:
                    category_counts[f"{description}_examples"] = matches[:5]  # First 5 examples
            error_counts[category] = category_counts

        return error_counts

    def _analyze_structure_quality(self, text: str) -> Dict[str, Any]:
        """Analyze the quality of structural elements"""
        lines = text.split('\n')

        # Check for consistent structure
        table_lines = [line for line in lines if '|' in line]
        header_candidates = [line for line in lines if line.isupper() and len(line.strip()) > 5]

        # Look for structure inconsistencies
        inconsistencies = {
            'table_column_variance': self._analyze_table_consistency(table_lines),
            'header_pattern_breaks': self._analyze_header_consistency(header_candidates),
            'paragraph_breaks': self._analyze_paragraph_structure(text),
            'reading_order_issues': self._check_reading_order(lines)
        }

        return inconsistencies

    def _analyze_tables(self, text: str) -> Dict[str, Any]:
        """Detailed analysis of table structure quality"""
        table_lines = [line for line in text.split('\n') if '|' in line]

        if not table_lines:
            return {'has_tables': False}

        # Analyze column consistency
        column_counts = [line.count('|') + 1 for line in table_lines]
        column_counter = Counter(column_counts)

        # Check for alignment issues
        alignment_issues = 0
        for line in table_lines:
            cells = line.split('|')
            # Check for cells that are too long or too short
            cell_lengths = [len(cell.strip()) for cell in cells]
            if max(cell_lengths) > 100 or min(cell_lengths) == 0:
                alignment_issues += 1

        return {
            'has_tables': True,
            'total_table_lines': len(table_lines),
            'column_distribution': dict(column_counter),
            'most_common_columns': column_counter.most_common(1)[0] if column_counter else None,
            'column_consistency': len(column_counter) <= 2,  # Good if only 1-2 different column counts
            'alignment_issues': alignment_issues,
            'alignment_issue_rate': alignment_issues / len(table_lines) if table_lines else 0
        }

    def _analyze_table_consistency(self, table_lines: List[str]) -> Dict[str, Any]:
        """Check if tables have consistent column structure"""
        if not table_lines:
            return {'no_tables': True}

        column_counts = [line.count('|') + 1 for line in table_lines]
        return {
            'min_columns': min(column_counts),
            'max_columns': max(column_counts),
            'variance': statistics.variance(column_counts) if len(column_counts) > 1 else 0,
            'consistency_score': 1 - (statistics.variance(column_counts) / statistics.mean(column_counts)) if column_counts else 0
        }

    def _analyze_header_consistency(self, headers: List[str]) -> Dict[str, Any]:
        """Check for consistent header patterns"""
        if not headers:
            return {'no_headers': True}

        # Look for patterns in header structure
        length_variance = statistics.variance([len(h) for h in headers]) if len(headers) > 1 else 0

        return {
            'header_count': len(headers),
            'avg_length': statistics.mean([len(h) for h in headers]),
            'length_variance': length_variance,
            'all_caps_rate': sum(1 for h in headers if h.isupper()) / len(headers)
        }

    def _analyze_paragraph_structure(self, text: str) -> Dict[str, Any]:
        """Analyze paragraph break consistency"""
        # Split by double newlines (paragraph breaks)
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

        if not paragraphs:
            return {'no_paragraphs': True}

        lengths = [len(p) for p in paragraphs]

        return {
            'paragraph_count': len(paragraphs),
            'avg_length': statistics.mean(lengths),
            'length_variance': statistics.variance(lengths) if len(lengths) > 1 else 0,
            'very_short_paragraphs': sum(1 for l in lengths if l < 50),
            'very_long_paragraphs': sum(1 for l in lengths if l > 2000)
        }

    def _check_reading_order(self, lines: List[str]) -> Dict[str, Any]:
        """Check for potential reading order issues"""
        issues = 0

        # Look for patterns that suggest reading order problems
        for i in range(len(lines) - 1):
            current = lines[i].strip()
            next_line = lines[i + 1].strip()

            # Check for abrupt topic changes (heuristic)
            if (current and next_line and
                len(current) > 50 and len(next_line) > 50 and
                not any(word in next_line.lower() for word in current.lower().split()[:5])):
                issues += 1

        return {
            'potential_order_issues': issues,
            'issue_rate': issues / len(lines) if lines else 0
        }

    def _analyze_readability(self, text: str) -> Dict[str, Any]:
        """Basic readability analysis"""
        words = text.split()
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not words or not sentences:
            return {'insufficient_text': True}

        avg_word_length = statistics.mean([len(w) for w in words])
        avg_sentence_length = statistics.mean([len(s.split()) for s in sentences])

        return {
            'avg_word_length': avg_word_length,
            'avg_sentence_length': avg_sentence_length,
            'total_sentences': len(sentences),
            'readability_score': self._simple_readability_score(avg_word_length, avg_sentence_length)
        }

    def _simple_readability_score(self, avg_word_len: float, avg_sent_len: float) -> float:
        """Simple readability heuristic (lower is easier)"""
        return (avg_word_len * 2) + (avg_sent_len * 0.5)

    def _analyze_historical_features(self, text: str) -> Dict[str, Any]:
        """Identify historical text features that might be confused with errors"""
        features = {}

        for category, patterns in self.historical_patterns.items():
            category_counts = {}
            for pattern, description in patterns:
                matches = re.findall(pattern, text)
                category_counts[description] = len(matches)
            features[category] = category_counts

        return features

def main():
    """Run comprehensive OCR quality analysis"""
    analyzer = OCRQualityAnalyzer()
    test_dir = Path("data/test_subset")

    print("=== COMPREHENSIVE OCR QUALITY ANALYSIS ===\n")

    all_results = []

    for json_file in sorted(test_dir.glob("*.json")):
        print(f"Analyzing {json_file.name}...")
        analysis = analyzer.analyze_file(json_file)
        all_results.append(analysis)

        # Print summary for each file
        print(f"\n--- {json_file.name} ---")
        stats = analysis['basic_stats']
        print(f"Pages: {stats['pages']}, Words: {stats['total_words']:,}, Chars/page: {stats['chars_per_page']:.0f}")

        # Error summary
        error_summary = []
        for category, errors in analysis['error_analysis'].items():
            total_errors = sum(v for k, v in errors.items() if not k.endswith('_examples'))
            if total_errors > 0:
                error_summary.append(f"{category}: {total_errors}")

        if error_summary:
            print(f"Potential errors: {', '.join(error_summary)}")
        else:
            print("No obvious OCR errors detected")

        # Table quality
        if analysis['table_analysis']['has_tables']:
            table_info = analysis['table_analysis']
            print(f"Tables: {table_info['total_table_lines']} lines, "
                  f"consistency: {'good' if table_info['column_consistency'] else 'poor'}, "
                  f"alignment issues: {table_info['alignment_issue_rate']:.1%}")

        print("-" * 50)

    # Overall summary
    print(f"\n=== OVERALL ASSESSMENT ===")

    # Aggregate statistics
    total_errors = sum(
        sum(sum(v for k, v in errors.items() if not k.endswith('_examples'))
            for errors in result['error_analysis'].values())
        for result in all_results
    )

    total_words = sum(result['basic_stats']['total_words'] for result in all_results)
    error_rate = total_errors / total_words if total_words > 0 else 0

    print(f"Total potential errors: {total_errors:,}")
    print(f"Total words: {total_words:,}")
    print(f"Estimated error rate: {error_rate:.3%}")

    # File-specific recommendations
    print(f"\nFile-specific observations:")
    for result in all_results:
        filename = result['file']
        if result['table_analysis']['has_tables']:
            table_quality = "good" if result['table_analysis']['column_consistency'] else "needs attention"
            print(f"- {filename}: Table structure {table_quality}")
        else:
            print(f"- {filename}: Simple text structure")

if __name__ == "__main__":
    main()