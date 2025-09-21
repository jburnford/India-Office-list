"""Debug script for Britannica document chunking issue."""

import sys
import json

sys.path.append('src')

from chunking.adaptive_chunker import AdaptiveChunkingOrchestrator, load_json_document

def debug_britannica():
    """Debug the Britannica document processing issue."""
    file_path = "extracted_json/output_1718f3a66eab1422763966bf5470b3b3906faa08/Firstedition1771-EncyclopaediaBritannicaorAdictionaryofartsandsciencescompileduponanewplanVolume2C-L.json"

    # Load document
    document = load_json_document(file_path)
    print(f"Document loaded - Text length: {len(document['text'])} characters")

    # Initialize orchestrator
    orchestrator = AdaptiveChunkingOrchestrator()

    try:
        # Analyze document DNA first
        profile = orchestrator.document_classifier.analyze(document)
        print(f"Document type: {profile.document_type}")
        print(f"Confidence: {profile.confidence}")

        # Get chunking strategy
        strategy = orchestrator.select_strategy(profile)
        print(f"Strategy: {strategy.__class__.__name__}")

        # Test chunking directly
        document_id = document.get('id', 'britannica_test')
        chunks = strategy.chunk(document['text'], document_id)
        print(f"Chunking successful! Created {len(chunks)} chunks")

        # Show first few chunks
        for i, chunk in enumerate(chunks[:3]):
            print(f"\nChunk {i+1}: {len(chunk.text)} chars")
            print(f"Preview: {chunk.text[:200]}...")

    except Exception as e:
        import traceback
        print(f"Error during processing: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    debug_britannica()