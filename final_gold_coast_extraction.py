"""
Final Gold Coast Section Extractor - Precise boundary detection
"""

import json
import re

def extract_precise_gold_coast_section():
    """Extract the exact Gold Coast section from the Colonial Office List."""

    # Load data
    with open('chunking_test_results.json', 'r', encoding='utf-8') as f:
        results = json.load(f)

    # Get Colonial Office List
    colonial_office_result = None
    for result in results['results']:
        if (result['document_profile']['document_type'] == 'administrative' and
            result['total_chars'] > 1000000):
            colonial_office_result = result
            break

    chunks = colonial_office_result['chunks']

    # Find start
    start_idx = None
    for i, chunk in enumerate(chunks):
        if 'THE GOLD COAST COLONY.' in chunk['text']:
            start_idx = i
            print(f"Gold Coast section starts at chunk {i}")
            break

    # Find end - look for next major section
    end_idx = len(chunks)

    for i in range(start_idx + 10, min(start_idx + 200, len(chunks))):  # Look within reasonable range
        chunk_text = chunks[i]['text']

        # Look for signs of transition to other colonies/territories
        # First check for explicit colony headers
        if re.search(r'(JAMAICA|BRITISH HONDURAS|LABUAN|LAGOS)\b(?!.*GOLD COAST)', chunk_text, re.IGNORECASE):
            end_idx = i
            print(f"Found transition to next section at chunk {i}: {chunk_text[:100]}...")
            break

        # Also check for pattern like "By the charter of..."" which often indicates new section
        if ('charter' in chunk_text.lower() and 'lagos' in chunk_text.lower() and
            'gold coast' in chunk_text.lower()):
            # This is the transition sentence - include it as it mentions Gold Coast
            end_idx = i + 1
            print(f"Found transition sentence at chunk {i}, including it")
            break

    if end_idx == len(chunks):
        print("No clear end found, using conservative estimate")
        end_idx = start_idx + 100  # Conservative estimate

    print(f"Extracting chunks {start_idx} to {end_idx-1} ({end_idx - start_idx} chunks)")

    gold_coast_chunks = chunks[start_idx:end_idx]
    return gold_coast_chunks

def display_gold_coast_section(chunks):
    """Display and analyze the Gold Coast section."""

    total_text = ""
    for chunk in chunks:
        total_text += chunk['text'] + "\n"

    print(f"\n🏴󠁧󠁢󠁧󠁨󠁿 GOLD COAST COLONY SECTION EXTRACTED")
    print("=" * 60)
    print(f"📊 Chunks: {len(chunks)}")
    print(f"📝 Total characters: {len(total_text):,}")

    # Key sections found
    sections = []
    if 'Situation, Area, and Native Tribes' in total_text:
        sections.append('Geography & Demographics')
    if 'Relations with Ashanti' in total_text:
        sections.append('Ashanti Relations')
    if 'Climate' in total_text:
        sections.append('Climate')
    if 'Revenue and Expenditure' in total_text:
        sections.append('Finance')
    if 'Judicial Department' in total_text:
        sections.append('Legal System')

    print(f"📋 Sections identified: {', '.join(sections)}")

    # Show first chunk (introduction)
    print(f"\n📖 INTRODUCTION:")
    print("-" * 40)
    first_chunk_preview = chunks[0]['text'][:800]
    print(first_chunk_preview)
    if len(chunks[0]['text']) > 800:
        print("...")

    # Show last chunk to verify boundary
    print(f"\n🔚 SECTION BOUNDARY:")
    print("-" * 40)
    last_chunk_preview = chunks[-1]['text'][-500:] if len(chunks[-1]['text']) > 500 else chunks[-1]['text']
    print("..." + last_chunk_preview if len(chunks[-1]['text']) > 500 else last_chunk_preview)

    return {
        'chunks': len(chunks),
        'characters': len(total_text),
        'sections': sections,
        'full_text': total_text
    }

def main():
    print("🔍 Final Gold Coast Section Extractor")
    print("=" * 50)

    try:
        gold_coast_chunks = extract_precise_gold_coast_section()
        analysis = display_gold_coast_section(gold_coast_chunks)

        # Save the precise extraction
        output = {
            'colony': 'Gold Coast',
            'source': 'Colonial Office List 1896',
            'extraction_method': 'Adaptive chunking + precise boundary detection',
            'statistics': {
                'chunks_extracted': analysis['chunks'],
                'total_characters': analysis['characters'],
                'sections_identified': analysis['sections']
            },
            'chunks': gold_coast_chunks,
            'full_text': analysis['full_text']
        }

        output_file = 'gold_coast_section_final.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        print(f"\n✅ Precise Gold Coast section saved to: {output_file}")
        print(f"🎯 Ready for RAG system integration!")

    except Exception as e:
        print(f"❌ Error during extraction: {e}")

if __name__ == "__main__":
    main()