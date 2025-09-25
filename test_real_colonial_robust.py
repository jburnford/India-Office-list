#!/usr/bin/env python3
"""
Test the robust detector on real Colonial Office List data
"""

import json
from improved_robust_detector import ImprovedColonyDetector

def test_on_colonial_office_list():
    """Test on the actual 1896 Colonial Office List"""

    filename = "./extracted_json/output_a29c9429212df7959632e22b6a667fd55654a592/ColonialOfficeList1896.json"

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)

        text = data['text']
        print(f"Colonial Office List 1896 - Text length: {len(text):,} characters")

        detector = ImprovedColonyDetector()

        # Find transitions
        transitions = detector.find_transitions(text)

        print(f"\nFound {len(transitions)} colony transitions:")

        for i, transition in enumerate(transitions):
            print(f"\nTransition {i+1}: {transition.description}")
            print(f"  Position: {transition.start_pos} → {transition.end_pos}")
            print(f"  Confidence: {transition.confidence}")

            # Show context around transition
            context_start = max(0, transition.start_pos - 150)
            context_end = min(len(text), transition.end_pos + 150)
            context = text[context_start:context_end]

            print(f"  Context:")
            print(f"    ...{context.replace(chr(10), ' ')[:200]}...")

        # Extract sections based on transitions
        sections = []

        if transitions:
            # First section (before first transition)
            first_section = text[:transitions[0].start_pos]
            if first_section.strip():
                sections.append({
                    'section_id': 0,
                    'text': first_section.strip(),
                    'description': 'Pre-colonial content (ads, front matter)'
                })

            # Sections between transitions
            for i, transition in enumerate(transitions):
                if i < len(transitions) - 1:
                    next_transition = transitions[i + 1]
                    section_text = text[transition.end_pos:next_transition.start_pos]
                else:
                    # Last section
                    section_text = text[transition.end_pos:]

                if section_text.strip():
                    sections.append({
                        'section_id': i + 1,
                        'text': section_text.strip(),
                        'description': f'Colony section {i+1}'
                    })

        print(f"\nExtracted {len(sections)} sections:")
        for section in sections:
            preview = section['text'][:100].replace('\n', ' ')
            print(f"  Section {section['section_id']}: {len(section['text'])} chars - {preview}...")

        # Save results
        output_file = "robust_extracted_sections.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(sections, f, indent=2, ensure_ascii=False)

        print(f"\nSaved to {output_file}")

        # Look for cases that might not start with "Situation and Area"
        print(f"\nAnalyzing section openings:")
        for section in sections[1:6]:  # Check first few colony sections
            first_lines = section['text'][:500]
            has_situation_area = 'Situation and Area' in first_lines
            print(f"  Section {section['section_id']}: {'✓' if has_situation_area else '✗'} 'Situation and Area'")
            if not has_situation_area:
                print(f"    Opens with: {first_lines[:100]}...")

    except Exception as e:
        print(f"Error processing file: {e}")

if __name__ == "__main__":
    test_on_colonial_office_list()