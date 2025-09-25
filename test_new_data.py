#!/usr/bin/env python3
"""
Quick test of chunking on newly extracted files
"""

import json
from pathlib import Path

def analyze_new_files():
    """Quick analysis of newly extracted files"""

    extracted_dir = Path("extracted_json")

    # Find all JSON files
    json_files = []
    for subdir in extracted_dir.iterdir():
        if subdir.is_dir():
            json_files.extend(list(subdir.glob("*.json")))

    print(f"Found {len(json_files)} extracted JSON files")

    # Analyze each file
    for json_file in json_files[:5]:  # First 5 files
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            text = data['text']
            metadata = data.get('metadata', {})

            print(f"\n--- {json_file.name} ---")
            print(f"Size: {len(text):,} chars")
            print(f"Pages: {metadata.get('pdf-total-pages', 'unknown')}")
            print(f"First 200 chars: {text[:200]}...")

            # Count structural elements
            paragraphs = len([p for p in text.split('\n\n') if p.strip()])
            tables = text.count('|')
            lines = len(text.split('\n'))

            print(f"Structure: {paragraphs} paragraphs, {tables} table markers, {lines} lines")

        except Exception as e:
            print(f"Error reading {json_file}: {e}")

def test_chunking_on_new_data():
    """Test our chunking strategies on one of the new files"""

    # Find a medium-sized file to test
    extracted_dir = Path("extracted_json")
    test_file = None

    for subdir in extracted_dir.iterdir():
        if subdir.is_dir():
            for json_file in subdir.glob("*.json"):
                file_size = json_file.stat().st_size
                if 100000 < file_size < 1000000:  # 100KB - 1MB range
                    test_file = json_file
                    break
        if test_file:
            break

    if not test_file:
        print("No suitable test file found")
        return

    print(f"\nTesting chunking on: {test_file.name}")

    with open(test_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    text = data['text']

    # Simple overlapping chunks test
    chunk_size = 800
    overlap = 200
    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk_text = text[start:end]

        # Try to break at sentence boundary
        if end < len(text):
            last_period = chunk_text.rfind('.')
            if last_period > chunk_size * 0.7:
                end = start + last_period + 1
                chunk_text = text[start:end]

        chunks.append(chunk_text)
        start = end - overlap

        if start >= len(text):
            break

    print(f"Created {len(chunks)} chunks")
    print(f"Avg chunk size: {sum(len(c) for c in chunks) / len(chunks):.0f} chars")

    # Show first chunk sample
    if chunks:
        print(f"First chunk: {chunks[0][:200]}...")

if __name__ == "__main__":
    analyze_new_files()
    test_chunking_on_new_data()