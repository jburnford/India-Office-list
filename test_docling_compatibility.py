#!/usr/bin/env python3
"""
Test DocLing compatibility with OLM-OCR JSON files
"""

import json
from pathlib import Path

def analyze_ocr_json_structure(file_path):
    """Analyze the structure of an OLM-OCR JSON file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"=== Analysis of {file_path.name} ===")
    print(f"File size: {file_path.stat().st_size / 1024:.1f} KB")
    print(f"Top-level keys: {list(data.keys())}")

    if 'text' in data:
        text = data['text']
        print(f"Text length: {len(text)} characters")
        print(f"First 200 characters: {text[:200]}...")

        # Check for structure markers
        structure_markers = {
            'headers': text.count('\n\n'),
            'tables': text.count('|'),
            'lists': text.count('\n-') + text.count('\n*'),
            'pages': text.count('\n\n\n'),
            'paragraphs': len([p for p in text.split('\n\n') if len(p.strip()) > 50])
        }
        print(f"Structure markers: {structure_markers}")

    if 'metadata' in data:
        metadata = data['metadata']
        print(f"Metadata: {metadata}")
        pages = metadata.get('pdf-total-pages', 1)
        print(f"Pages: {pages}")

    if 'attributes' in data:
        attributes = data['attributes']
        print(f"Attributes: {list(attributes.keys())}")

    print("-" * 50)

def main():
    """Test compatibility with our OLM-OCR JSON files"""
    test_dir = Path("data/test_subset")

    print("Analyzing OLM-OCR JSON file structure for DocLing compatibility...\n")

    # Test small files first
    small_files = [f for f in test_dir.glob("*.json") if f.stat().st_size < 10000]
    large_files = [f for f in test_dir.glob("*.json") if f.stat().st_size >= 10000]

    print("=== SMALL FILES (easier to process) ===")
    for file_path in small_files[:3]:  # Test first 3 small files
        analyze_ocr_json_structure(file_path)

    print("\n=== LARGE FILES (multi-page documents) ===")
    for file_path in large_files[:2]:  # Test first 2 large files
        analyze_ocr_json_structure(file_path)

    print("\n=== DOCLING COMPATIBILITY ASSESSMENT ===")
    print("DocLing supports:")
    print("✓ PDF, DOCX, images (original formats)")
    print("✓ JSON input (specifically 'Docling JSON')")
    print("✓ Plain text processing")
    print("\nOur OLM-OCR format:")
    print("- JSON with 'text', 'metadata', 'attributes' fields")
    print("- Already extracted text from PDFs via OLM-OCR")
    print("- Contains page boundary and structure information")
    print("\nRecommendation:")
    print("1. Extract 'text' field from JSON and feed to DocLing as plain text")
    print("2. Use DocLing for structural analysis of extracted text")
    print("3. Combine DocLing structure with OLM-OCR metadata")
    print("4. Alternative: Create text files and use DocLing text processing")

if __name__ == "__main__":
    main()