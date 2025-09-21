"""
Test script for adaptive chunking system.

This script tests the adaptive chunking framework on sample documents
from the extracted_json directory, validating chunking quality by
reading and analyzing the results.
"""

import sys
import json
from pathlib import Path

# Add src to path so we can import our modules
sys.path.append('src')

from chunking.adaptive_chunker import AdaptiveChunkingOrchestrator, load_json_document
from chunking.document_dna_analyzer import DocumentType

def test_single_document(file_path: str, orchestrator: AdaptiveChunkingOrchestrator):
    """Test chunking on a single document and analyze results."""
    print(f"\n{'='*60}")
    print(f"Testing: {Path(file_path).name}")
    print(f"{'='*60}")

    try:
        # Load document
        document = load_json_document(file_path)
        print(f"Document loaded - Text length: {len(document['text'])} characters")

        # Process through adaptive chunking
        result = orchestrator.chunk_document(document)

        # Display analysis results
        profile = result['document_profile']
        print(f"\nDocument DNA Analysis:")
        print(f"  Type: {profile['document_type']}")
        print(f"  Confidence: {profile['confidence']:.2f}")
        print(f"  Features detected:")
        for key, value in profile['features'].items():
            if isinstance(value, list) and len(value) > 0:
                print(f"    {key}: {len(value)} items")
            elif isinstance(value, (int, float)) and value > 0:
                print(f"    {key}: {value}")

        # Display chunking results
        print(f"\nChunking Results:")
        print(f"  Strategy used: {result['processing_metadata']['strategy_used']}")
        print(f"  Number of chunks: {result['chunk_count']}")
        print(f"  Average chunk size: {result['avg_chunk_size']:.0f} characters")

        # Analyze chunk distribution
        chunk_sizes = [chunk['metadata']['size'] for chunk in result['chunks']]
        print(f"  Chunk size range: {min(chunk_sizes)} - {max(chunk_sizes)} characters")

        # Show first few chunks with their content
        print(f"\nSample Chunks:")
        for i, chunk in enumerate(result['chunks'][:3]):  # Show first 3 chunks
            chunk_text = chunk['text']
            preview = chunk_text[:200] + "..." if len(chunk_text) > 200 else chunk_text
            print(f"\n  Chunk {i+1} ({len(chunk_text)} chars):")
            print(f"    Metadata: {chunk['metadata'].get('type', 'N/A')}")
            if 'colonial_discourse_markers' in chunk['metadata']:
                markers = chunk['metadata']['colonial_discourse_markers']
                if markers:
                    print(f"    Colonial discourse markers: {len(markers)}")
            print(f"    Preview: {preview}")

        # Check for colonial discourse flagging
        colonial_chunks = [c for c in result['chunks']
                         if c['metadata'].get('colonial_discourse_detected', False)]
        if colonial_chunks:
            print(f"\n  Colonial discourse detected in {len(colonial_chunks)} chunks")

        return result

    except Exception as e:
        print(f"Error processing document: {e}")
        return None

def main():
    """Main test function."""
    print("Adaptive Chunking System Test")
    print("Testing on sample documents from extracted_json/")

    # Initialize orchestrator
    orchestrator = AdaptiveChunkingOrchestrator()

    # Test documents (representative samples)
    test_files = [
        "extracted_json/output_1718f3a66eab1422763966bf5470b3b3906faa08/Firstedition1771-EncyclopaediaBritannicaorAdictionaryofartsandsciencescompileduponanewplanVolume2C-L.json",
        "extracted_json/output_a29c9429212df7959632e22b6a667fd55654a592/ColonialOfficeList1896.json",
        "extracted_json/output_3f7adf03b620a0968cba7066b3456fce203dd8b4/1919-022258_complete.json"
    ]

    results = []

    for file_path in test_files:
        if Path(file_path).exists():
            result = test_single_document(file_path, orchestrator)
            if result:
                results.append(result)
        else:
            print(f"\nWarning: File not found: {file_path}")

    # Generate overall statistics
    if results:
        print(f"\n{'='*60}")
        print("OVERALL STATISTICS")
        print(f"{'='*60}")

        stats = orchestrator.get_chunking_statistics(results)
        print(f"Documents processed: {stats['successful_documents']}/{stats['total_documents']}")
        print(f"Document types identified:")
        for doc_type, count in stats['document_type_distribution'].items():
            print(f"  {doc_type}: {count}")

        print(f"Chunking strategies used:")
        for strategy, count in stats['strategies_used'].items():
            print(f"  {strategy}: {count}")

        chunk_stats = stats['chunk_statistics']
        print(f"Chunk statistics:")
        print(f"  Total chunks: {chunk_stats['total_chunks']}")
        print(f"  Average size: {chunk_stats['average_size']:.0f} characters")
        print(f"  Size range: {chunk_stats['min_size']} - {chunk_stats['max_size']}")

        # Save detailed results for analysis
        output_file = "chunking_test_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'results': results,
                'statistics': stats
            }, f, indent=2, ensure_ascii=False)
        print(f"\nDetailed results saved to: {output_file}")

if __name__ == "__main__":
    main()