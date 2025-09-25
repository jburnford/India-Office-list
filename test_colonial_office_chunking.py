#!/usr/bin/env python3
"""
Test chunking strategies specifically on Colonial Office List 1896
This represents the challenging administrative colonial documents
"""

import json
from pathlib import Path
import re

def analyze_colonial_office_structure():
    """Analyze the structure of the Colonial Office List"""

    colonial_file = Path("extracted_json/output_a29c9429212df7959632e22b6a667fd55654a592/ColonialOfficeList1896.json")

    if not colonial_file.exists():
        print("Colonial Office List file not found")
        return

    with open(colonial_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    text = data['text']
    metadata = data.get('metadata', {})

    print("=== COLONIAL OFFICE LIST 1896 ANALYSIS ===")
    print(f"File size: {len(text):,} characters")
    print(f"Pages: {metadata.get('pdf-total-pages', 'unknown')}")

    # Analyze structure patterns
    lines = text.split('\n')
    print(f"Total lines: {len(lines):,}")

    # Look for different types of content
    table_lines = [line for line in lines if '|' in line]
    header_candidates = [line for line in lines if line.isupper() and len(line.strip()) > 10]

    print(f"Lines with tables (|): {len(table_lines):,}")
    print(f"Potential headers (all caps): {len(header_candidates)}")

    # Sample different sections
    print(f"\n--- FIRST 500 CHARACTERS ---")
    print(text[:500])

    print(f"\n--- SAMPLE FROM MIDDLE ---")
    mid_point = len(text) // 2
    print(text[mid_point:mid_point + 500])

    # Look for specific colonial administrative patterns
    patterns = {
        'rank_patterns': len(re.findall(r'\b(Colonel|Major|Captain|Lieutenant|Governor|Secretary)\b', text, re.IGNORECASE)),
        'location_patterns': len(re.findall(r'\b(Ceylon|India|Burma|Hong Kong|Jamaica|Barbados|Trinidad)\b', text, re.IGNORECASE)),
        'date_patterns': len(re.findall(r'\b(18\d{2}|19\d{2})\b', text)),
        'administrative_terms': len(re.findall(r'\b(Colonial Office|Crown Colony|Protectorate|Administration)\b', text, re.IGNORECASE))
    }

    print(f"\n--- COLONIAL DOCUMENT PATTERNS ---")
    for pattern, count in patterns.items():
        print(f"{pattern}: {count} occurrences")

    return text

def test_chunking_strategies_colonial(text):
    """Test different chunking approaches on colonial text"""

    print(f"\n=== CHUNKING STRATEGY TESTING ===")

    strategies = {}

    # Strategy 1: Simple overlapping chunks
    def overlapping_chunks(text, size=1000, overlap=200):
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + size, len(text))
            chunk = text[start:end]

            # Try to break at paragraph boundary
            if end < len(text):
                last_para = chunk.rfind('\n\n')
                if last_para > size * 0.6:
                    end = start + last_para
                    chunk = text[start:end]

            chunks.append(chunk)
            start = end - overlap
            if start >= len(text):
                break
        return chunks

    strategies['overlapping_1000'] = overlapping_chunks(text, 1000, 200)

    # Strategy 2: Paragraph-based chunks
    def paragraph_chunks(text, max_paragraphs=3):
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        chunks = []

        for i in range(0, len(paragraphs), max_paragraphs):
            chunk_paras = paragraphs[i:i + max_paragraphs]
            chunks.append('\n\n'.join(chunk_paras))

        return chunks

    strategies['paragraph_3'] = paragraph_chunks(text, 3)

    # Strategy 3: Structure-aware (headers and sections)
    def structure_aware_chunks(text):
        lines = text.split('\n')
        chunks = []
        current_chunk = []

        for line in lines:
            # Check if this is likely a major header (all caps, substantial length)
            if (line.isupper() and len(line.strip()) > 15 and
                not line.strip().startswith('|') and len(current_chunk) > 5):

                # Save previous chunk
                if current_chunk:
                    chunks.append('\n'.join(current_chunk))
                    current_chunk = [line]
                else:
                    current_chunk.append(line)
            else:
                current_chunk.append(line)

                # If chunk gets too large, split it
                if len('\n'.join(current_chunk)) > 1500:
                    chunks.append('\n'.join(current_chunk))
                    current_chunk = []

        # Add final chunk
        if current_chunk:
            chunks.append('\n'.join(current_chunk))

        return chunks

    strategies['structure_aware'] = structure_aware_chunks(text)

    # Strategy 4: Table-aware chunks (preserve table integrity)
    def table_aware_chunks(text):
        lines = text.split('\n')
        chunks = []
        current_chunk = []
        in_table = False

        for line in lines:
            is_table_line = '|' in line and line.count('|') >= 2

            if is_table_line and not in_table:
                # Starting a table - may need to start new chunk
                if len('\n'.join(current_chunk)) > 800:
                    chunks.append('\n'.join(current_chunk))
                    current_chunk = [line]
                else:
                    current_chunk.append(line)
                in_table = True

            elif not is_table_line and in_table:
                # Ending a table
                current_chunk.append(line)
                in_table = False

            else:
                current_chunk.append(line)

                # Split if chunk gets too large (but not in middle of table)
                if not in_table and len('\n'.join(current_chunk)) > 1200:
                    chunks.append('\n'.join(current_chunk))
                    current_chunk = []

        # Add final chunk
        if current_chunk:
            chunks.append('\n'.join(current_chunk))

        return chunks

    strategies['table_aware'] = table_aware_chunks(text)

    # Analyze results
    print(f"{'Strategy':<20} {'Chunks':<8} {'Avg Size':<10} {'Min Size':<10} {'Max Size':<10}")
    print("-" * 70)

    for name, chunks in strategies.items():
        if chunks:
            sizes = [len(chunk) for chunk in chunks]
            print(f"{name:<20} {len(chunks):<8} {sum(sizes)//len(sizes):<10} {min(sizes):<10} {max(sizes):<10}")

            # Show sample of first chunk
            print(f"  First chunk sample: {chunks[0][:100].replace(chr(10), ' ')}...")
            print()

    return strategies

def analyze_colonial_content_types(text):
    """Identify different types of content in the colonial document"""

    print(f"\n=== COLONIAL CONTENT TYPE ANALYSIS ===")

    # Look for different sections based on content patterns
    sections = {
        'personnel_lists': 0,
        'administrative_rules': 0,
        'geographic_listings': 0,
        'financial_records': 0,
        'correspondence': 0
    }

    # Sample analysis on chunks to identify content types
    chunks = text.split('\n\n')[:100]  # First 100 paragraphs

    for chunk in chunks:
        chunk_lower = chunk.lower()

        # Personnel patterns
        if any(rank in chunk_lower for rank in ['governor', 'secretary', 'officer', 'clerk', 'chief']):
            sections['personnel_lists'] += 1

        # Administrative rules
        if any(word in chunk_lower for word in ['regulation', 'rule', 'procedure', 'shall be', 'appointed']):
            sections['administrative_rules'] += 1

        # Geographic content
        if any(place in chunk_lower for place in ['colony', 'province', 'district', 'territory', 'island']):
            sections['geographic_listings'] += 1

        # Financial records
        if any(fin in chunk_lower for fin in ['£', 'salary', 'allowance', 'pension', 'expense']):
            sections['financial_records'] += 1

        # Correspondence patterns
        if any(corr in chunk_lower for corr in ['letter', 'despatch', 'telegram', 'dated', 'received']):
            sections['correspondence'] += 1

    print("Content type distribution (first 100 paragraphs):")
    for content_type, count in sections.items():
        print(f"  {content_type}: {count}")

    return sections

def main():
    """Main analysis of Colonial Office List chunking"""

    # Analyze document structure
    text = analyze_colonial_office_structure()

    if not text:
        return

    # Test chunking strategies
    strategies = test_chunking_strategies_colonial(text)

    # Analyze content types
    content_analysis = analyze_colonial_content_types(text)

    # Summary and recommendations
    print(f"\n=== CHUNKING RECOMMENDATIONS FOR COLONIAL DOCUMENTS ===")

    print("Key challenges identified:")
    print("1. Mixed content types (personnel, administrative, geographic)")
    print("2. Complex table structures requiring preservation")
    print("3. Hierarchical administrative organization")
    print("4. Dense factual information with names, dates, locations")

    print("\nRecommended approach:")
    print("- Use table-aware chunking to preserve administrative records")
    print("- Structure-aware chunking for major section boundaries")
    print("- Moderate chunk sizes (800-1200 chars) to capture complete entries")
    print("- Overlap strategy for maintaining context across personnel listings")

if __name__ == "__main__":
    main()