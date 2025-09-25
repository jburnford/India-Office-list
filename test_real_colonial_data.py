#!/usr/bin/env python3
"""
Test colony transition detection on real Colonial Office List data
"""

import json
import sys
from test_colony_transition_detection import ColonyTransitionDetector

def test_on_real_data():
    """Test on actual Colonial Office List JSON file"""

    # Try to find a real JSON file to test with
    import glob

    json_files = glob.glob("*.json")[:5]  # Test on first 5 files

    if not json_files:
        print("No JSON files found in current directory")
        return

    detector = ColonyTransitionDetector()

    for filename in json_files:
        print(f"\n=== TESTING: {filename} ===")

        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Extract text content
            if isinstance(data, dict) and 'text' in data:
                text = data['text']
            elif isinstance(data, list) and len(data) > 0:
                # Handle chunked data format
                text_parts = []
                for item in data[:10]:  # Test first 10 chunks
                    if isinstance(item, dict) and 'text' in item:
                        text_parts.append(item['text'])
                text = '\n\n'.join(text_parts)
            else:
                print(f"Unrecognized JSON structure in {filename}")
                continue

            print(f"Text length: {len(text):,} characters")

            # Detect transitions
            signals = detector.detect_transitions(text)
            boundaries = detector.find_transition_boundaries(text)

            print(f"Found {len(signals['colony_ends'])} colony end signals")
            print(f"Found {len(signals['colony_starts'])} colony start signals")
            print(f"Found {len(boundaries)} colony boundaries")

            # Show first few boundaries
            for i, (start, end, desc) in enumerate(boundaries[:3]):
                print(f"\nBoundary {i+1}: {desc}")

                # Show context around transition
                context_start = max(0, start - 100)
                context_end = min(len(text), end + 100)
                context = text[context_start:context_end]

                print("Context:")
                print("-" * 40)
                print(context.replace('\n', ' ').strip())
                print("-" * 40)

            if len(boundaries) > 3:
                print(f"... and {len(boundaries) - 3} more boundaries")

        except Exception as e:
            print(f"Error processing {filename}: {e}")

def extract_colony_sections(filename: str, output_file: str = None):
    """Extract individual colony sections using transition detection"""

    detector = ColonyTransitionDetector()

    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Extract text
    if isinstance(data, dict) and 'text' in data:
        text = data['text']
    else:
        print("Expected JSON with 'text' field")
        return

    boundaries = detector.find_transition_boundaries(text)

    if not boundaries:
        print("No colony boundaries detected")
        return

    # Extract sections
    sections = []

    # Add text before first boundary as first section
    if boundaries:
        first_section = text[:boundaries[0][0]]
        if first_section.strip():
            sections.append({
                'section_id': 0,
                'text': first_section.strip(),
                'start_pos': 0,
                'end_pos': boundaries[0][0]
            })

    # Extract sections between boundaries
    for i, (boundary_start, boundary_end, desc) in enumerate(boundaries):
        if i < len(boundaries) - 1:
            # Section from end of this boundary to start of next
            next_boundary_start = boundaries[i + 1][0]
            section_text = text[boundary_end:next_boundary_start]
        else:
            # Last section to end of document
            section_text = text[boundary_end:]

        if section_text.strip():
            sections.append({
                'section_id': i + 1,
                'text': section_text.strip(),
                'start_pos': boundary_end,
                'end_pos': boundaries[i + 1][0] if i < len(boundaries) - 1 else len(text),
                'boundary_description': desc
            })

    print(f"Extracted {len(sections)} colony sections")

    # Save results
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(sections, f, indent=2, ensure_ascii=False)
        print(f"Saved sections to {output_file}")

    # Show section summaries
    for section in sections:
        preview = section['text'][:200].replace('\n', ' ')
        print(f"Section {section['section_id']}: {len(section['text'])} chars - {preview}...")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Extract sections from specific file
        filename = sys.argv[1]
        output_file = filename.replace('.json', '_extracted_sections.json')
        extract_colony_sections(filename, output_file)
    else:
        # Test on available files
        test_on_real_data()