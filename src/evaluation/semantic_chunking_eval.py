#!/usr/bin/env python3
"""
Semantic evaluation of chunking strategies using embeddings
Step 2: Measure topical coherence and clustering quality
"""

import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA
from sklearn.metrics.pairwise import cosine_similarity
import matplotlib.pyplot as plt
import seaborn as sns

@dataclass
class EmbeddedChunk:
    """Chunk with its embedding"""
    text: str
    embedding: np.ndarray
    strategy: str
    doc_id: str
    chunk_id: str
    start_pos: int
    end_pos: int

class SemanticChunkingEvaluator:
    """Evaluates chunking quality using semantic embeddings"""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        print(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.embeddings_cache = {}

    def embed_chunks(self, chunks: List[Dict[str, Any]]) -> List[EmbeddedChunk]:
        """Create embeddings for chunks"""
        print(f"Creating embeddings for {len(chunks)} chunks...")

        texts = [chunk['text'] for chunk in chunks]

        # Create embeddings in batches for efficiency
        embeddings = self.model.encode(texts, show_progress_bar=True)

        embedded_chunks = []
        for i, chunk in enumerate(chunks):
            embedded_chunks.append(EmbeddedChunk(
                text=chunk['text'],
                embedding=embeddings[i],
                strategy=chunk['strategy'],
                doc_id=chunk['doc_id'],
                chunk_id=chunk['chunk_id'],
                start_pos=chunk.get('start_pos', 0),
                end_pos=chunk.get('end_pos', 0)
            ))

        return embedded_chunks

    def evaluate_topical_coherence(self, embedded_chunks: List[EmbeddedChunk]) -> Dict[str, Any]:
        """Measure how well chunks cluster by topic"""

        if len(embedded_chunks) < 3:
            return {"error": "Need at least 3 chunks for clustering"}

        embeddings = np.array([chunk.embedding for chunk in embedded_chunks])

        # Try different numbers of clusters
        cluster_range = range(2, min(len(embedded_chunks), 8))
        silhouette_scores = []
        best_k = 2

        for k in cluster_range:
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(embeddings)
            score = silhouette_score(embeddings, cluster_labels)
            silhouette_scores.append(score)

            if score == max(silhouette_scores):
                best_k = k

        # Use best k for final clustering
        kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(embeddings)

        return {
            'best_k': best_k,
            'best_silhouette_score': max(silhouette_scores),
            'silhouette_scores': silhouette_scores,
            'cluster_labels': cluster_labels.tolist(),
            'cluster_centers': kmeans.cluster_centers_
        }

    def evaluate_strategy_coherence(self, embedded_chunks: List[EmbeddedChunk]) -> Dict[str, Any]:
        """Compare coherence across different chunking strategies"""

        strategy_results = {}

        # Group chunks by strategy
        strategies = {}
        for chunk in embedded_chunks:
            if chunk.strategy not in strategies:
                strategies[chunk.strategy] = []
            strategies[chunk.strategy].append(chunk)

        for strategy, chunks in strategies.items():
            if len(chunks) < 2:
                continue

            embeddings = np.array([chunk.embedding for chunk in chunks])

            # Calculate intra-strategy similarity
            similarities = cosine_similarity(embeddings)

            # Remove diagonal (self-similarity)
            mask = ~np.eye(similarities.shape[0], dtype=bool)
            avg_similarity = similarities[mask].mean()

            # Calculate spread (variance in embeddings)
            embedding_variance = np.var(embeddings, axis=0).mean()

            strategy_results[strategy] = {
                'chunk_count': len(chunks),
                'avg_internal_similarity': float(avg_similarity),
                'embedding_variance': float(embedding_variance),
                'coherence_score': float(avg_similarity - embedding_variance)  # Higher similarity, lower variance = better
            }

        return strategy_results

    def analyze_topic_transitions(self, embedded_chunks: List[EmbeddedChunk]) -> Dict[str, Any]:
        """Analyze how well chunking captures topic transitions"""

        # Sort chunks by document position
        sorted_chunks = sorted(embedded_chunks, key=lambda x: (x.doc_id, x.start_pos))

        transition_scores = []
        topic_breaks = []

        for i in range(len(sorted_chunks) - 1):
            current = sorted_chunks[i]
            next_chunk = sorted_chunks[i + 1]

            # Skip if different documents
            if current.doc_id != next_chunk.doc_id:
                continue

            # Calculate semantic similarity between adjacent chunks
            similarity = cosine_similarity(
                current.embedding.reshape(1, -1),
                next_chunk.embedding.reshape(1, -1)
            )[0, 0]

            transition_scores.append(similarity)

            # Low similarity suggests topic break
            if similarity < 0.5:  # Threshold for topic change
                topic_breaks.append({
                    'position': i,
                    'similarity': float(similarity),
                    'before': current.text[:100],
                    'after': next_chunk.text[:100]
                })

        return {
            'avg_transition_similarity': float(np.mean(transition_scores)) if transition_scores else 0,
            'topic_breaks_detected': len(topic_breaks),
            'topic_breaks': topic_breaks[:5],  # First 5 examples
            'transition_scores': transition_scores
        }

    def compare_chunking_strategies(self, chunks_by_strategy: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """Compare multiple chunking strategies semantically"""

        results = {}

        for strategy, chunks in chunks_by_strategy.items():
            if len(chunks) < 2:
                print(f"Skipping {strategy}: too few chunks")
                continue

            print(f"\nEvaluating {strategy} ({len(chunks)} chunks)...")

            # Convert to embedded chunks
            embedded_chunks = self.embed_chunks(chunks)

            # Evaluate topical coherence
            coherence_results = self.evaluate_topical_coherence(embedded_chunks)

            # Evaluate strategy coherence
            strategy_coherence = self.evaluate_strategy_coherence(embedded_chunks)

            # Analyze topic transitions
            transition_analysis = self.analyze_topic_transitions(embedded_chunks)

            results[strategy] = {
                'topical_coherence': coherence_results,
                'strategy_coherence': strategy_coherence,
                'transition_analysis': transition_analysis,
                'chunk_count': len(chunks)
            }

        return results

    def visualize_embeddings(self, embedded_chunks: List[EmbeddedChunk], output_path: str):
        """Create 2D visualization of chunk embeddings"""

        if len(embedded_chunks) < 3:
            print("Need at least 3 chunks for visualization")
            return

        # Reduce dimensionality for visualization
        embeddings = np.array([chunk.embedding for chunk in embedded_chunks])
        pca = PCA(n_components=2)
        embeddings_2d = pca.fit_transform(embeddings)

        # Create visualization
        plt.figure(figsize=(12, 8))

        # Color by strategy
        strategies = list(set(chunk.strategy for chunk in embedded_chunks))
        colors = plt.cm.Set1(np.linspace(0, 1, len(strategies)))
        strategy_colors = dict(zip(strategies, colors))

        for chunk, (x, y) in zip(embedded_chunks, embeddings_2d):
            plt.scatter(x, y, c=[strategy_colors[chunk.strategy]],
                       label=chunk.strategy, alpha=0.7, s=60)

        plt.xlabel(f'PCA Component 1 ({pca.explained_variance_ratio_[0]:.1%} variance)')
        plt.ylabel(f'PCA Component 2 ({pca.explained_variance_ratio_[1]:.1%} variance)')
        plt.title('Chunk Embeddings by Chunking Strategy')

        # Remove duplicate labels
        handles, labels = plt.gca().get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        plt.legend(by_label.values(), by_label.keys())

        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"Visualization saved to {output_path}")

def create_test_chunks():
    """Create test chunks from our sample data for demonstration"""

    # Read sample text
    test_file = Path("data/test_subset/3200801612.json")
    with open(test_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    text = data['text']

    # Create chunks using different strategies manually for demo
    chunks_by_strategy = {
        'overlapping_600': [],
        'paragraph_based': [],
        'structure_aware': []
    }

    # Overlapping chunks (600 chars, 150 overlap)
    chunk_size = 600
    overlap = 150
    start = 0
    chunk_id = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk_text = text[start:end]

        chunks_by_strategy['overlapping_600'].append({
            'text': chunk_text,
            'strategy': 'overlapping_600',
            'doc_id': 'test_doc',
            'chunk_id': f"overlap_{chunk_id}",
            'start_pos': start,
            'end_pos': end
        })

        start = end - overlap
        chunk_id += 1
        if start >= len(text):
            break

    # Paragraph-based chunks
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    for i in range(0, len(paragraphs), 2):
        para_group = paragraphs[i:i+2]
        chunks_by_strategy['paragraph_based'].append({
            'text': '\n\n'.join(para_group),
            'strategy': 'paragraph_based',
            'doc_id': 'test_doc',
            'chunk_id': f"para_{i//2}",
            'start_pos': 0,  # Simplified for demo
            'end_pos': len('\n\n'.join(para_group))
        })

    # Structure-aware (manual for demo)
    parts = text.split('\n\n')
    chunks_by_strategy['structure_aware'].append({
        'text': parts[0],  # Header
        'strategy': 'structure_aware',
        'doc_id': 'test_doc',
        'chunk_id': 'struct_0',
        'start_pos': 0,
        'end_pos': len(parts[0])
    })

    if len(parts) > 1:
        chunks_by_strategy['structure_aware'].append({
            'text': '\n\n'.join(parts[1:]),  # Main content
            'strategy': 'structure_aware',
            'doc_id': 'test_doc',
            'chunk_id': 'struct_1',
            'start_pos': len(parts[0]),
            'end_pos': len(text)
        })

    return chunks_by_strategy

def main():
    """Run semantic chunking evaluation"""
    print("=== SEMANTIC CHUNKING EVALUATION ===")

    # Create test chunks
    chunks_by_strategy = create_test_chunks()

    print(f"Created chunks:")
    for strategy, chunks in chunks_by_strategy.items():
        print(f"  {strategy}: {len(chunks)} chunks")

    # Initialize evaluator
    evaluator = SemanticChunkingEvaluator()

    # Compare strategies
    results = evaluator.compare_chunking_strategies(chunks_by_strategy)

    # Print results
    print(f"\n=== SEMANTIC EVALUATION RESULTS ===")

    for strategy, result in results.items():
        print(f"\n{strategy.upper()}:")
        print(f"  Chunks: {result['chunk_count']}")

        if 'topical_coherence' in result:
            tc = result['topical_coherence']
            if 'best_silhouette_score' in tc:
                print(f"  Best silhouette score: {tc['best_silhouette_score']:.3f}")
                print(f"  Optimal clusters: {tc['best_k']}")

        if strategy in result.get('strategy_coherence', {}):
            sc = result['strategy_coherence'][strategy]
            print(f"  Internal similarity: {sc['avg_internal_similarity']:.3f}")
            print(f"  Coherence score: {sc['coherence_score']:.3f}")

        if 'transition_analysis' in result:
            ta = result['transition_analysis']
            print(f"  Avg transition similarity: {ta['avg_transition_similarity']:.3f}")
            print(f"  Topic breaks detected: {ta['topic_breaks_detected']}")

    # Save results
    with open('semantic_evaluation_results.json', 'w') as f:
        # Convert numpy arrays to lists for JSON serialization
        json_results = {}
        for strategy, result in results.items():
            json_result = {}
            for key, value in result.items():
                if isinstance(value, dict):
                    json_value = {}
                    for k, v in value.items():
                        if isinstance(v, np.ndarray):
                            json_value[k] = v.tolist()
                        else:
                            json_value[k] = v
                    json_result[key] = json_value
                else:
                    json_result[key] = value
            json_results[strategy] = json_result

        json.dump(json_results, f, indent=2)

    print(f"\nResults saved to semantic_evaluation_results.json")

if __name__ == "__main__":
    main()