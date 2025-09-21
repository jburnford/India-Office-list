"""
Adaptive Chunking Orchestrator - Main interface for the adaptive chunking system.

This module implements the central orchestrator that ties together document DNA
analysis with specialized chunking strategies. It provides the main interface
for the adaptive chunking framework.
"""

import json
from typing import List, Dict, Optional
from dataclasses import asdict

from .document_dna_analyzer import DocumentDNAAnalyzer, DocumentType, DocumentProfile
from .chunking_strategies import (
    BaseChunker, ReferenceChunker, AdministrativeChunker,
    GovernmentReportChunker, HybridChunker, Chunk
)

class AdaptiveChunkingOrchestrator:
    """
    Main orchestrator for adaptive chunking system.

    Analyzes document DNA and applies appropriate chunking strategy.
    Provides unified interface for processing diverse historical documents.
    """

    def __init__(self):
        self.document_classifier = DocumentDNAAnalyzer()

        # Initialize specialized chunking strategies
        self.chunking_strategies = {
            DocumentType.REFERENCE: ReferenceChunker(),
            DocumentType.ADMINISTRATIVE: AdministrativeChunker(),
            DocumentType.GOVERNMENT_REPORT: GovernmentReportChunker(),
            DocumentType.NARRATIVE: HybridChunker(),  # Use hybrid for now
            DocumentType.LEGAL: HybridChunker(),      # Use hybrid for now
            DocumentType.HYBRID: HybridChunker()
        }

    def chunk_document(self, document: Dict) -> Dict:
        """
        Process a document through the adaptive chunking pipeline.

        Args:
            document: Dictionary containing 'text' and optionally 'id', 'metadata'

        Returns:
            Dictionary containing chunks, document profile, and processing metadata
        """
        # Step 1: Analyze document DNA
        doc_profile = self.document_classifier.analyze(document)

        # Step 2: Select optimal chunking strategy
        strategy = self.select_strategy(doc_profile)

        # Step 3: Configure strategy with document-specific parameters
        self._configure_strategy(strategy, doc_profile)

        # Step 4: Apply chunking
        document_id = document.get('id', 'unknown')
        chunks = strategy.chunk(document['text'], document_id)

        # Filter out empty chunks
        chunks = [chunk for chunk in chunks if chunk.text.strip()]

        # Step 5: Post-process chunks with additional metadata
        enhanced_chunks = self._enhance_chunks(chunks, doc_profile)

        # Step 6: Compile results
        # Convert document profile to dict and make it JSON serializable
        profile_dict = asdict(doc_profile)
        profile_dict['document_type'] = doc_profile.document_type.value  # Convert enum to string

        result = {
            'document_id': document_id,
            'document_profile': profile_dict,
            'chunks': [asdict(chunk) for chunk in enhanced_chunks],
            'chunk_count': len(enhanced_chunks),
            'total_chars': len(document['text']),
            'avg_chunk_size': sum(len(chunk.text) for chunk in enhanced_chunks) / len(enhanced_chunks) if enhanced_chunks else 0,
            'processing_metadata': {
                'strategy_used': strategy.__class__.__name__,
                'confidence': doc_profile.confidence,
                'document_type': doc_profile.document_type.value
            }
        }

        return result

    def select_strategy(self, doc_profile: DocumentProfile) -> BaseChunker:
        """Select the appropriate chunking strategy based on document profile."""
        return self.chunking_strategies[doc_profile.document_type]

    def _configure_strategy(self, strategy: BaseChunker, doc_profile: DocumentProfile):
        """Configure chunking strategy with document-specific parameters."""
        min_size, max_size = doc_profile.suggested_chunk_size
        strategy.min_size = min_size
        strategy.max_size = max_size

    def _enhance_chunks(self, chunks: List[Chunk], doc_profile: DocumentProfile) -> List[Chunk]:
        """Add additional metadata to chunks based on document analysis."""
        enhanced_chunks = []

        for i, chunk in enumerate(chunks):
            # Add document-level metadata
            chunk.metadata.update({
                'document_type': doc_profile.document_type.value,
                'document_confidence': doc_profile.confidence,
                'chunk_index': i,
                'colonial_discourse_detected': len(doc_profile.features.get('colonial_markers', [])) > 0
            })

            # Add bias flags for colonial discourse
            if doc_profile.features.get('colonial_markers'):
                chunk.metadata['bias_flags'] = {
                    'colonial_discourse': True,
                    'markers_detected': doc_profile.features['colonial_markers']
                }

            enhanced_chunks.append(chunk)

        return enhanced_chunks

    def process_multiple_documents(self, documents: List[Dict]) -> List[Dict]:
        """Process multiple documents through the adaptive chunking pipeline."""
        results = []

        for doc in documents:
            try:
                result = self.chunk_document(doc)
                results.append(result)
            except Exception as e:
                # Log error and continue with next document
                error_result = {
                    'document_id': doc.get('id', 'unknown'),
                    'error': str(e),
                    'chunks': [],
                    'chunk_count': 0
                }
                results.append(error_result)

        return results

    def get_chunking_statistics(self, results: List[Dict]) -> Dict:
        """Generate statistics about chunking results."""
        if not results:
            return {}

        total_docs = len(results)
        successful_docs = len([r for r in results if 'error' not in r])

        # Document type distribution
        doc_types = {}
        chunk_size_stats = []
        strategies_used = {}

        for result in results:
            if 'error' in result:
                continue

            # Document type counting
            doc_type = result['processing_metadata']['document_type']
            doc_types[doc_type] = doc_types.get(doc_type, 0) + 1

            # Strategy usage
            strategy = result['processing_metadata']['strategy_used']
            strategies_used[strategy] = strategies_used.get(strategy, 0) + 1

            # Chunk size statistics
            for chunk_data in result['chunks']:
                chunk_size_stats.append(chunk_data['metadata']['size'])

        # Calculate chunk size statistics
        avg_chunk_size = sum(chunk_size_stats) / len(chunk_size_stats) if chunk_size_stats else 0
        min_chunk_size = min(chunk_size_stats) if chunk_size_stats else 0
        max_chunk_size = max(chunk_size_stats) if chunk_size_stats else 0

        return {
            'total_documents': total_docs,
            'successful_documents': successful_docs,
            'error_rate': (total_docs - successful_docs) / total_docs if total_docs > 0 else 0,
            'document_type_distribution': doc_types,
            'strategies_used': strategies_used,
            'chunk_statistics': {
                'total_chunks': len(chunk_size_stats),
                'average_size': avg_chunk_size,
                'min_size': min_chunk_size,
                'max_size': max_chunk_size
            }
        }


def load_json_document(file_path: str) -> Dict:
    """Load a JSON document from file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_chunking_results(results: Dict, output_path: str):
    """Save chunking results to JSON file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)