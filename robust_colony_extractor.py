#!/usr/bin/env python3
"""
Robust Colony Extractor - Based on Gemini's finditer approach
============================================================

Uses a more robust regex pattern to find complete colony blocks instead of
trying to split on boundaries. This should fix the fundamental boundary
detection issue where Basutoland was including Bermuda content.
"""

import re
import json
from typing import Dict, List

def final_robust_colony_extractor(text: str) -> Dict[str, str]:
    """
    Extracts colonies from the full text using a robust find-and-iterate method
    that is resilient to different newline characters and whitespace.

    Returns:
        A dictionary mapping colony names to their full text.
    """
    colonies = {}

    # This robust pattern uses \s+ to match various kinds of newlines and whitespace.
    # It finds a colony heading (group 1) and all its content (group 2)
    # until the next heading or the end of the string is found.
    pattern = re.compile(
        r'([A-Z\s,]+)\.\s+(.*?)(?=\s+[A-Z\s,]+\.\s+|\Z)',
        re.DOTALL  # Allows '.' to match newline characters
    )

    # The '---' is a visual separator we can remove for cleaner processing.
    cleaned_text = text.replace('\n\n---\n\n', '\n\n')

    # Iterate over all non-overlapping matches in the string
    for match in re.finditer(pattern, cleaned_text):
        colony_name = match.group(1).strip()

        # We reconstruct the full text for the colony, including its heading.
        colony_text = f"{colony_name}.\n\n{match.group(2).strip()}"

        colonies[colony_name] = colony_text

    return colonies

def test_robust_extractor():
    """Test the robust extractor on the 1896 Colonial Office List"""

    filename = "./extracted_json/output_a29c9429212df7959632e22b6a667fd55654a592/ColonialOfficeList1896.json"

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)

        text = data['text']
        print(f"Processing Colonial Office List ({len(text):,} characters)")

        # Extract colonies using robust method
        colonies = final_robust_colony_extractor(text)

        print(f"\n=== ROBUST EXTRACTION RESULTS ===")
        print(f"Total colonies found: {len(colonies)}")

        # Check if we properly separated Basutoland and Bermuda
        print(f"\n=== BOUNDARY DETECTION TEST ===")

        if 'BASUTOLAND' in colonies:
            basutoland_text = colonies['BASUTOLAND']
            print(f"BASUTOLAND: {len(basutoland_text):,} chars")
            print(f"  Contains BERMUDA: {'BERMUDA' in basutoland_text}")
            print(f"  Starts with: {basutoland_text[:100]}...")
            print(f"  Ends with: ...{basutoland_text[-100:]}")

        if 'BERMUDA' in colonies:
            bermuda_text = colonies['BERMUDA']
            print(f"\nBERMUDA: {len(bermuda_text):,} chars")
            print(f"  Starts with: {bermuda_text[:100]}...")
            print(f"  Ends with: ...{bermuda_text[-100:]}")

        # Show first 15 colonies found
        print(f"\n=== FIRST 15 COLONIES ===")
        for i, (name, text) in enumerate(list(colonies.items())[:15]):
            print(f"  {i+1:2d}. {name:40s} ({len(text):6,} chars)")

        # Test for Canadian provinces
        print(f"\n=== CANADIAN PROVINCES TEST ===")
        canadian_provinces = ['ONTARIO', 'QUEBEC', 'NOVA SCOTIA', 'NEW BRUNSWICK', 'MANITOBA']
        found_provinces = []
        for province in canadian_provinces:
            if province in colonies:
                found_provinces.append(province)
                print(f"  ✓ Found: {province}")

        if found_provinces:
            print(f"Found {len(found_provinces)} Canadian provinces as separate entries")
            print("This confirms the original problem - provinces should be grouped under Canada")

        # Save results for further analysis
        output_file = "robust_extraction_results.json"
        results = {
            'total_colonies': len(colonies),
            'colony_names': list(colonies.keys()),
            'extraction_method': 'robust_finditer',
            'boundary_test': {
                'basutoland_contains_bermuda': 'BERMUDA' in colonies.get('BASUTOLAND', ''),
                'proper_separation': 'BASUTOLAND' in colonies and 'BERMUDA' in colonies
            }
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"\nResults saved to {output_file}")

        return colonies

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return {}

def compare_with_broken_version():
    """Compare robust extraction with the broken dominion_aware results"""

    print("\n" + "="*60)
    print("COMPARING ROBUST VS BROKEN EXTRACTION")
    print("="*60)

    # Load broken results
    try:
        with open('dominion_aware_extraction.json', 'r') as f:
            broken_data = json.load(f)

        print(f"BROKEN VERSION:")
        print(f"  Total territories: {len(broken_data['territories'])}")

        basutoland_broken = broken_data['territories'][0]  # First territory
        print(f"  BASUTOLAND size: {basutoland_broken['size']:,} chars")
        print(f"  Contains BERMUDA: {'BERMUDA' in basutoland_broken['text']}")

    except Exception as e:
        print(f"Could not load broken results: {e}")

    # Test robust version
    colonies = test_robust_extractor()

    if colonies:
        print(f"\nROBUST VERSION:")
        print(f"  Total colonies: {len(colonies)}")
        if 'BASUTOLAND' in colonies:
            print(f"  BASUTOLAND size: {len(colonies['BASUTOLAND']):,} chars")
            print(f"  Contains BERMUDA: {'BERMUDA' in colonies['BASUTOLAND']}")

        print(f"\n✅ IMPROVEMENT: Proper boundary detection {'achieved' if not ('BERMUDA' in colonies.get('BASUTOLAND', '')) else 'FAILED'}")

if __name__ == "__main__":
    compare_with_broken_version()