#!/usr/bin/env python3
"""
Refined Robust Extractor
========================

Builds on Gemini's approach but adds filtering to focus on actual colonies
and avoid advertisements and other non-territory content.
"""

import re
import json
from typing import Dict, List, Tuple

def extract_colonies_section(text: str) -> str:
    """Extract just the colonies section from the full document"""

    # Use known working boundaries for 1896
    start_pos = 210954  # Start of BASUTOLAND
    end_pos = 1886549   # Start of APPENDIX

    return text[start_pos:end_pos]

def refined_robust_colony_extractor(text: str) -> Dict[str, str]:
    """
    Refined version of Gemini's approach:
    1. Extract just the colonies section
    2. Use robust regex for boundary detection
    3. Filter out obvious non-colonies
    """

    # Step 1: Extract colonies section only
    colonies_text = extract_colonies_section(text)
    print(f"Colonies section: {len(colonies_text):,} chars")

    # Step 2: Apply Gemini's robust regex within colonies section
    colonies = {}

    # Improved pattern - handles start of text and markdown formatting
    pattern = re.compile(
        r'(?:^|(?:\n\n(?:---\n\n)?))(?:\*\*)?([A-Z][A-Z\s\-\']+)\.(?:\*\*)?\s*\n\n(.*?)(?=(?:\n\n(?:---\n\n)?(?:\*\*)?[A-Z][A-Z\s\-\']+\.(?:\*\*)?\s*\n\n)|\Z)',
        re.DOTALL | re.MULTILINE
    )

    for match in re.finditer(pattern, colonies_text):
        colony_name = match.group(1).strip()
        colony_content = match.group(2).strip()

        # Step 3: Filter out obvious non-colonies
        if is_valid_colony(colony_name, colony_content):
            colony_text = f"{colony_name}.\n\n{colony_content}"
            colonies[colony_name] = colony_text

    return colonies

def is_valid_colony(name: str, content: str) -> bool:
    """Filter out advertisements and non-colony content"""

    # Must be substantial content
    if len(content) < 500:
        return False

    # Exclude obvious advertisements
    ad_indicators = [
        'LIMITED', 'COMPANY', 'SAUCE', 'PIANO', 'CREAM', 'PREPARATION',
        'WHOLESALE', 'RETAIL', 'PRICE', 'CATALOGUE', 'DELIVERY',
        'MANUFACTURER', 'SOLD EVERYWHERE'
    ]

    if any(indicator in name.upper() for indicator in ad_indicators):
        return False

    # Must have geographic or administrative content
    good_indicators = [
        'situation', 'area', 'population', 'government', 'history',
        'climate', 'colony', 'territory', 'governor', 'commissioner',
        'square miles', 'inhabitants', 'administration', 'revenue'
    ]

    content_lower = content.lower()
    has_good_content = sum(1 for indicator in good_indicators if indicator in content_lower)

    return has_good_content >= 2  # Must have at least 2 territory indicators

def test_refined_extractor():
    """Test the refined extractor"""

    filename = "./extracted_json/output_a29c9429212df7959632e22b6a667fd55654a592/ColonialOfficeList1896.json"

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)

        text = data['text']
        print(f"Processing Colonial Office List ({len(text):,} characters)")

        # Extract colonies using refined method
        colonies = refined_robust_colony_extractor(text)

        print(f"\n=== REFINED EXTRACTION RESULTS ===")
        print(f"Total valid colonies: {len(colonies)}")

        # Test boundary detection
        print(f"\n=== BOUNDARY DETECTION TEST ===")

        if 'BASUTOLAND' in colonies:
            basutoland = colonies['BASUTOLAND']
            print(f"✓ BASUTOLAND: {len(basutoland):,} chars")
            print(f"  Contains BERMUDA: {'BERMUDA' in basutoland}")

        if 'BERMUDA' in colonies:
            bermuda = colonies['BERMUDA']
            print(f"✓ BERMUDA: {len(bermuda):,} chars")
            print(f"  Starts properly: {bermuda.startswith('BERMUDA.')}")

        # Show known good territories
        known_good = [
            'BASUTOLAND', 'BERMUDA', 'BRITISH GUIANA', 'BRITISH HONDURAS',
            'GIBRALTAR', 'JAMAICA', 'MAURITIUS', 'HONG KONG', 'CEYLON'
        ]

        print(f"\n=== KNOWN GOOD TERRITORIES ===")
        found_good = 0
        for territory in known_good:
            if territory in colonies:
                found_good += 1
                size = len(colonies[territory])
                print(f"  ✓ {territory:20s} ({size:6,} chars)")
            else:
                print(f"  ✗ {territory:20s} (missing)")

        print(f"\nFound {found_good}/{len(known_good)} known good territories ({found_good/len(known_good)*100:.1f}%)")

        # Show all found colonies
        print(f"\n=== ALL COLONIES FOUND ===")
        for i, (name, text) in enumerate(sorted(colonies.items()), 1):
            print(f"  {i:2d}. {name:35s} ({len(text):6,} chars)")

        # Canadian provinces test
        canadian_provinces = ['ONTARIO', 'QUEBEC', 'NOVA SCOTIA', 'NEW BRUNSWICK', 'MANITOBA']
        found_provinces = [p for p in canadian_provinces if p in colonies]

        print(f"\n=== CANADIAN PROVINCES ===")
        print(f"Found as separate colonies: {found_provinces}")
        if found_provinces:
            print("⚠️  These should be grouped under DOMINION OF CANADA")

        # Save results
        output = {
            'total_colonies': len(colonies),
            'known_good_found': found_good,
            'known_good_total': len(known_good),
            'accuracy_percentage': found_good/len(known_good)*100,
            'boundary_test_passed': 'BASUTOLAND' in colonies and 'BERMUDA' in colonies and 'BERMUDA' not in colonies.get('BASUTOLAND', ''),
            'colonies': list(colonies.keys())
        }

        with open('refined_extraction_results.json', 'w') as f:
            json.dump(output, f, indent=2)

        print(f"\nResults saved to refined_extraction_results.json")

        return colonies

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return {}

if __name__ == "__main__":
    test_refined_extractor()