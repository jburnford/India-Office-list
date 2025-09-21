"""
Refined Gold Coast Section Extractor

More precise extraction that stops at the appropriate boundary.
"""

import json
import re

def load_chunking_results():
    with open('chunking_test_results.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def find_gold_coast_section():
    """Find and extract the precise Gold Coast section."""
    results = load_chunking_results()

    # Get Colonial Office List
    colonial_office_result = None
    for result in results['results']:
        if (result['document_profile']['document_type'] == 'administrative' and
            result['total_chars'] > 1000000):
            colonial_office_result = result
            break

    chunks = colonial_office_result['chunks']

    # Find start of Gold Coast section
    start_idx = None
    for i, chunk in enumerate(chunks):
        if re.search(r'THE\s+GOLD\s+COAST\s+COLONY\.\s*\n', chunk['text'], re.IGNORECASE):
            start_idx = i
            print(f"Found Gold Coast section start at chunk {i}")
            break

    if start_idx is None:
        print("Could not find Gold Coast section start")
        return

    # Find end of Gold Coast section - look for next major colony heading
    end_idx = len(chunks)

    # Look for patterns that indicate next sections
    next_section_patterns = [
        r'^LAGOS\.?\s*$',
        r'^THE\s+LAGOS\s+COLONY',
        r'^SIERRA\s+LEONE\.?\s*$',
        r'^THE\s+SIERRA\s+LEONE\s+COLONY',
        r'^BRITISH\s+HONDURAS\.?\s*$',
        r'^GAMBIA\.?\s*$'
    ]

    for i in range(start_idx + 1, len(chunks)):
        chunk_text = chunks[i]['text'].strip()

        # Check for next major section
        for pattern in next_section_patterns:
            if re.search(pattern, chunk_text, re.IGNORECASE):
                end_idx = i
                print(f"Found next section '{chunk_text[:50]}...' at chunk {i}")
                break

        if end_idx < len(chunks):
            break

        # Also check for other administrative sections that might end Gold Coast
        if (len(chunk_text) < 200 and
            any(keyword in chunk_text.upper() for keyword in ['COLONY', 'PROTECTORATE', 'TERRITORY']) and
            'GOLD COAST' not in chunk_text.upper()):
            end_idx = i
            print(f"Found potential section boundary at chunk {i}: '{chunk_text}'")
            break

    print(f"Extracting chunks {start_idx} to {end_idx-1} ({end_idx - start_idx} chunks)")

    gold_coast_chunks = chunks[start_idx:end_idx]

    return gold_coast_chunks

def analyze_section(chunks):
    """Analyze the Gold Coast section content."""
    total_text = ""
    subsections = []

    for chunk in chunks:
        total_text += chunk['text'] + "\n"

    # Look for major subsections
    subsection_patterns = [
        r'Situation,?\s+Area,?\s+and\s+Native\s+Tribes',
        r'Relations\s+with\s+Ashanti',
        r'Climate',
        r'Revenue\s+and\s+Expenditure',
        r'Judicial\s+Department',
        r'Public\s+Works\s+Department',
        r'Education\s+Department',
        r'Medical\s+Department'
    ]

    for pattern in subsection_patterns:
        if re.search(pattern, total_text, re.IGNORECASE):
            subsections.append(pattern.replace(r'\s+', ' ').replace(r',?\s+', ', '))

    return {
        'total_chunks': len(chunks),
        'total_characters': len(total_text),
        'subsections_found': subsections,
        'sample_text': total_text[:1000] + "..." if len(total_text) > 1000 else total_text
    }

def main():
    print("Refined Gold Coast Section Extractor")
    print("=" * 50)

    gold_coast_section = find_gold_coast_section()

    if gold_coast_section:
        analysis = analyze_section(gold_coast_section)

        print(f"\nGOLD COAST SECTION EXTRACTED")
        print("=" * 30)
        print(f"Chunks: {analysis['total_chunks']}")
        print(f"Characters: {analysis['total_characters']:,}")
        print(f"Subsections found: {len(analysis['subsections_found'])}")

        print(f"\nSubsections:")
        for subsection in analysis['subsections_found']:
            print(f"  - {subsection}")

        print(f"\nSample content:")
        print("-" * 20)
        print(analysis['sample_text'])

        # Save the refined extraction
        output = {
            'colony': 'Gold Coast',
            'chunks_extracted': len(gold_coast_section),
            'total_characters': analysis['total_characters'],
            'subsections': analysis['subsections_found'],
            'chunks': gold_coast_section
        }

        with open('gold_coast_section_refined.json', 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        print(f"\nRefined extraction saved to: gold_coast_section_refined.json")

if __name__ == "__main__":
    main()