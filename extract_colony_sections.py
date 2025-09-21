"""
Colony Section Extractor - Extract specific colony sections from chunked Colonial Office List.

This script demonstrates how the adaptive chunking system enables targeted extraction
of specific colonial administrative sections from large historical documents.
"""

import json
import re
from typing import List, Dict, Tuple

def load_chunking_results(file_path: str) -> Dict:
    """Load the chunking results from JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def find_colony_section_chunks(chunks: List[Dict], colony_name: str) -> List[Tuple[int, Dict]]:
    """
    Find all chunks related to a specific colony.

    Returns list of (chunk_index, chunk) tuples for the colony section.
    """
    colony_chunks = []

    # Search for chunks containing the colony name
    for i, chunk in enumerate(chunks):
        text = chunk['text']

        # Check for main section header (e.g., "THE GOLD COAST COLONY")
        if re.search(rf'THE\s+{re.escape(colony_name.upper())}\s+COLONY', text, re.IGNORECASE):
            colony_chunks.append((i, chunk))
            print(f"Found main section header in chunk {i}")

        # Check for other mentions
        elif re.search(rf'\b{re.escape(colony_name)}\b', text, re.IGNORECASE):
            colony_chunks.append((i, chunk))

    return colony_chunks

def extract_continuous_section(chunks: List[Dict], start_chunk_idx: int, colony_name: str) -> List[Dict]:
    """
    Extract a continuous section starting from the main colony header.

    Continues until we hit the next major colony section or end of document.
    """
    section_chunks = []

    # Known West African colonies that might follow Gold Coast
    next_colonies = ['SIERRA LEONE', 'LAGOS', 'GAMBIA', 'BRITISH HONDURAS']

    i = start_chunk_idx
    while i < len(chunks):
        chunk = chunks[i]
        text = chunk['text']

        # Check if we've hit the next major colony section
        hit_next_section = False
        for next_colony in next_colonies:
            if re.search(rf'^{re.escape(next_colony)}\.?\s*$', text.strip(), re.IGNORECASE):
                hit_next_section = True
                print(f"Found next section '{next_colony}' at chunk {i}, stopping extraction")
                break
            if re.search(rf'THE\s+{re.escape(next_colony)}\s+COLONY', text, re.IGNORECASE):
                hit_next_section = True
                print(f"Found next section header '{next_colony}' at chunk {i}, stopping extraction")
                break

        if hit_next_section:
            break

        # Check for other major section breaks
        if (re.search(r'^[A-Z\s]{10,}\.?\s*$', text.strip()) and
            not re.search(rf'{re.escape(colony_name)}', text, re.IGNORECASE) and
            len(text.strip()) < 100):
            print(f"Found potential section break at chunk {i}: '{text.strip()[:50]}...'")
            # Only break if this looks like a major heading
            if any(keyword in text.upper() for keyword in ['COLONY', 'PROTECTORATE', 'TERRITORY']):
                break

        section_chunks.append(chunk)
        i += 1

    return section_chunks

def analyze_colony_content(section_chunks: List[Dict]) -> Dict:
    """Analyze the content structure of a colony section."""
    total_chars = sum(len(chunk['text']) for chunk in section_chunks)

    # Look for different content types
    content_types = {
        'geographical': 0,
        'historical': 0,
        'administrative': 0,
        'judicial': 0,
        'financial': 0,
        'personnel': 0
    }

    personnel_entries = []

    for chunk in section_chunks:
        text = chunk['text']

        # Classify content
        if re.search(r'(Situation|Area|Native Tribes|Climate|bounded)', text, re.IGNORECASE):
            content_types['geographical'] += 1
        if re.search(r'(history|expedition|treaty|company|1672|1874)', text, re.IGNORECASE):
            content_types['historical'] += 1
        if re.search(r'(administration|commissioner|government|colonial secretary)', text, re.IGNORECASE):
            content_types['administrative'] += 1
        if re.search(r'(judge|court|justice|attorney)', text, re.IGNORECASE):
            content_types['judicial'] += 1
        if re.search(r'(revenue|expenditure|£|salary)', text, re.IGNORECASE):
            content_types['financial'] += 1

        # Extract personnel entries (salary information)
        salary_matches = re.findall(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),?\s+([A-Z][a-zA-Z\s,]+),?\s+(\d{1,3},?\d{3}[ls]\.?)', text)
        personnel_entries.extend(salary_matches)

    return {
        'total_chunks': len(section_chunks),
        'total_characters': total_chars,
        'content_breakdown': content_types,
        'personnel_count': len(personnel_entries),
        'sample_personnel': personnel_entries[:5]  # First 5 entries
    }

def main():
    """Main extraction function."""
    print("Colony Section Extractor")
    print("=" * 50)

    # Load chunking results
    results = load_chunking_results('chunking_test_results.json')

    # Get Colonial Office List chunks - it's the larger administrative document
    colonial_office_result = None
    for result in results['results']:
        if (result['document_profile']['document_type'] == 'administrative' and
            result['total_chars'] > 1000000):  # Larger than 1MB
            colonial_office_result = result
            break

    if not colonial_office_result:
        print("Could not find Colonial Office List in results")
        return

    chunks = colonial_office_result['chunks']
    print(f"Found Colonial Office List with {len(chunks)} chunks")

    # Extract Gold Coast section
    colony_name = "GOLD COAST"
    print(f"\nSearching for {colony_name} section...")

    # Find all mentions
    gold_coast_chunks = find_colony_section_chunks(chunks, colony_name)
    print(f"Found {len(gold_coast_chunks)} chunks mentioning {colony_name}")

    # Find the main section header
    main_section_idx = None
    for chunk_idx, chunk in gold_coast_chunks:
        if re.search(rf'THE\s+{re.escape(colony_name)}\s+COLONY', chunk['text'], re.IGNORECASE):
            main_section_idx = chunk_idx
            print(f"Found main section at chunk {chunk_idx}")
            break

    if main_section_idx is None:
        print("Could not find main Gold Coast section header")
        return

    # Extract continuous section
    print(f"\nExtracting continuous section starting from chunk {main_section_idx}...")
    section_chunks = extract_continuous_section(chunks, main_section_idx, colony_name)

    print(f"Extracted {len(section_chunks)} chunks for Gold Coast section")

    # Analyze content
    analysis = analyze_colony_content(section_chunks)

    print(f"\n{colony_name} SECTION ANALYSIS")
    print("=" * 40)
    print(f"Total chunks: {analysis['total_chunks']}")
    print(f"Total characters: {analysis['total_characters']:,}")
    print(f"Personnel entries found: {analysis['personnel_count']}")

    print(f"\nContent breakdown:")
    for content_type, count in analysis['content_breakdown'].items():
        if count > 0:
            print(f"  {content_type.title()}: {count} chunks")

    # Show section overview
    print(f"\n{colony_name} SECTION CONTENT")
    print("=" * 40)

    for i, chunk in enumerate(section_chunks[:5]):  # Show first 5 chunks
        preview = chunk['text'][:200] + "..." if len(chunk['text']) > 200 else chunk['text']
        print(f"\nChunk {i+1}:")
        print(f"  Size: {len(chunk['text'])} chars")
        print(f"  Preview: {preview}")

    if len(section_chunks) > 5:
        print(f"\n... and {len(section_chunks) - 5} more chunks")

    # Sample personnel entries
    if analysis['sample_personnel']:
        print(f"\nSAMPLE PERSONNEL ENTRIES:")
        print("-" * 25)
        for name, title, salary in analysis['sample_personnel']:
            print(f"  {name}: {title} - {salary}")

    # Save extracted section
    output_data = {
        'colony': colony_name,
        'extraction_info': {
            'start_chunk_index': main_section_idx,
            'total_chunks_extracted': len(section_chunks),
            'source_document': colonial_office_result['document_id']
        },
        'analysis': analysis,
        'chunks': section_chunks
    }

    output_file = f"gold_coast_section_extracted.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\nExtracted section saved to: {output_file}")

if __name__ == "__main__":
    main()