#!/usr/bin/env python3
"""
Quick test of chunking strategies on a single small file
"""

import json
from src.chunking.chunking_comparison import ChunkingComparator
from pathlib import Path

def test_single_file():
    """Test chunking on one small file"""
    # Test on smallest file first
    test_file = Path("data/test_subset/3200797029.json")

    with open(test_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    text = data['text']
    print(f"Testing file: {test_file.name}")
    print(f"Text length: {len(text)} characters")
    print(f"Pages: {data.get('metadata', {}).get('pdf-total-pages', 1)}")

    # Test each strategy individually
    from src.chunking.chunking_comparison import OverlappingChunker, StructureAwareChunker, ParagraphChunker

    strategies = [
        OverlappingChunker(chunk_size=600, overlap=150),
        ParagraphChunker(max_paragraphs=2),
        StructureAwareChunker()
    ]

    print(f"\nTesting chunking strategies:")
    print("-" * 50)

    for strategy in strategies:
        chunks = strategy.chunk(text, "test")
        lengths = [len(chunk.text) for chunk in chunks]

        print(f"{strategy.name}:")
        print(f"  Chunks: {len(chunks)}")
        print(f"  Avg length: {sum(lengths)/len(lengths):.0f} chars")
        print(f"  Range: {min(lengths)}-{max(lengths)} chars")

        # Show first chunk as example
        if chunks:
            print(f"  First chunk: {chunks[0].text[:100]}...")
        print()

if __name__ == "__main__":
    test_single_file()