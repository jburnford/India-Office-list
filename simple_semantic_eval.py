#!/usr/bin/env python3
"""
Simple semantic evaluation using basic text similarity measures
Fallback when sentence-transformers has issues
"""

import json
import re
from pathlib import Path
from collections import Counter
from typing import List, Dict, Any, Set
import math

class SimpleSemanticEvaluator:
    """Evaluate chunking using basic text similarity measures"""

    def __init__(self):
        self.stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'was', 'are', 'were', 'be', 'been', 'have',
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'may', 'might', 'can', 'this', 'that', 'these', 'those', 'i', 'you',
            'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'
        }

    def extract_keywords(self, text: str, top_k: int = 20) -> List[str]:
        """Extract key terms from text using TF-IDF-like scoring"""

        # Clean and tokenize
        text = re.sub(r'[^a-zA-Z\s]', ' ', text.lower())
        words = text.split()

        # Remove stopwords and short words
        words = [w for w in words if len(w) > 3 and w not in self.stopwords]

        # Count frequencies
        word_counts = Counter(words)

        # Simple TF scoring (could enhance with IDF if we had corpus)
        total_words = len(words)
        tf_scores = {word: count/total_words for word, count in word_counts.items()}

        # Return top keywords
        return sorted(tf_scores.keys(), key=lambda x: tf_scores[x], reverse=True)[:top_k]

    def calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts using keyword overlap"""

        keywords1 = set(self.extract_keywords(text1, 50))
        keywords2 = set(self.extract_keywords(text2, 50))

        if not keywords1 or not keywords2:
            return 0.0

        # Jaccard similarity
        intersection = len(keywords1.intersection(keywords2))
        union = len(keywords1.union(keywords2))

        return intersection / union if union > 0 else 0.0

    def analyze_topic_coherence(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze how well chunks cluster by topic using keyword similarity"""

        if len(chunks) < 2:
            return {"error": "Need at least 2 chunks"}

        # Calculate pairwise similarities
        similarities = []
        chunk_keywords = []

        for chunk in chunks:
            keywords = set(self.extract_keywords(chunk['text'], 30))
            chunk_keywords.append(keywords)

        # Calculate all pairwise similarities
        for i in range(len(chunks)):
            for j in range(i + 1, len(chunks)):
                sim = self.calculate_text_similarity(chunks[i]['text'], chunks[j]['text'])
                similarities.append(sim)

        avg_similarity = sum(similarities) / len(similarities) if similarities else 0

        # Find most similar pairs (potential topics)
        similarity_threshold = 0.3
        related_pairs = [(i, j, sim) for i, sim in enumerate(similarities) if sim > similarity_threshold]

        return {
            'avg_similarity': avg_similarity,
            'max_similarity': max(similarities) if similarities else 0,
            'min_similarity': min(similarities) if similarities else 0,
            'related_pairs_count': len(related_pairs),
            'coherence_score': avg_similarity
        }

    def analyze_topic_transitions(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze topic transitions between adjacent chunks"""

        if len(chunks) < 2:
            return {"error": "Need at least 2 chunks"}

        # Sort chunks by position if available
        try:
            sorted_chunks = sorted(chunks, key=lambda x: x.get('start_pos', 0))
        except:
            sorted_chunks = chunks

        transition_similarities = []
        topic_breaks = []

        for i in range(len(sorted_chunks) - 1):
            current = sorted_chunks[i]
            next_chunk = sorted_chunks[i + 1]

            # Skip if different documents
            if current.get('doc_id') != next_chunk.get('doc_id'):
                continue

            sim = self.calculate_text_similarity(current['text'], next_chunk['text'])
            transition_similarities.append(sim)

            # Low similarity suggests topic break
            if sim < 0.2:
                topic_breaks.append({
                    'position': i,
                    'similarity': sim,
                    'before_keywords': self.extract_keywords(current['text'], 10),
                    'after_keywords': self.extract_keywords(next_chunk['text'], 10)
                })

        return {
            'avg_transition_similarity': sum(transition_similarities) / len(transition_similarities) if transition_similarities else 0,
            'topic_breaks_detected': len(topic_breaks),
            'topic_breaks': topic_breaks[:3],  # First 3 examples
            'transition_count': len(transition_similarities)
        }

    def analyze_strategy_coherence(self, chunks_by_strategy: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """Compare coherence across chunking strategies"""

        results = {}

        for strategy, chunks in chunks_by_strategy.items():
            if len(chunks) < 2:
                continue

            # Analyze topical coherence
            coherence = self.analyze_topic_coherence(chunks)

            # Analyze transitions
            transitions = self.analyze_topic_transitions(chunks)

            # Extract key themes for the strategy
            all_text = ' '.join([chunk['text'] for chunk in chunks])
            top_keywords = self.extract_keywords(all_text, 15)

            # Calculate chunk size statistics
            chunk_lengths = [len(chunk['text']) for chunk in chunks]
            avg_length = sum(chunk_lengths) / len(chunk_lengths)
            length_variance = sum((l - avg_length) ** 2 for l in chunk_lengths) / len(chunk_lengths)

            results[strategy] = {
                'chunk_count': len(chunks),
                'avg_chunk_length': avg_length,
                'length_variance': length_variance,
                'topical_coherence': coherence,
                'transition_analysis': transitions,
                'top_keywords': top_keywords,
                'overall_score': coherence.get('coherence_score', 0) * 0.7 +
                               transitions.get('avg_transition_similarity', 0) * 0.3
            }

        return results

def create_test_chunks_from_file(file_path: Path) -> Dict[str, List[Dict]]:
    """Create test chunks from a single file"""

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    text = data['text']
    doc_id = file_path.stem

    chunks_by_strategy = {
        'overlapping_800': [],
        'overlapping_1200': [],
        'paragraph_2': [],
        'paragraph_4': []
    }

    # Overlapping chunks - 800 chars
    chunk_size = 800
    overlap = 200
    start = 0
    chunk_id = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk_text = text[start:end]

        chunks_by_strategy['overlapping_800'].append({
            'text': chunk_text,
            'strategy': 'overlapping_800',
            'doc_id': doc_id,
            'chunk_id': f"overlap800_{chunk_id}",
            'start_pos': start,
            'end_pos': end
        })

        start = end - overlap
        chunk_id += 1
        if start >= len(text):
            break

    # Overlapping chunks - 1200 chars
    chunk_size = 1200
    overlap = 250
    start = 0
    chunk_id = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk_text = text[start:end]

        chunks_by_strategy['overlapping_1200'].append({
            'text': chunk_text,
            'strategy': 'overlapping_1200',
            'doc_id': doc_id,
            'chunk_id': f"overlap1200_{chunk_id}",
            'start_pos': start,
            'end_pos': end
        })

        start = end - overlap
        chunk_id += 1
        if start >= len(text):
            break

    # Paragraph-based chunks
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

    # 2 paragraphs per chunk
    for i in range(0, len(paragraphs), 2):
        para_group = paragraphs[i:i+2]
        if para_group:
            chunks_by_strategy['paragraph_2'].append({
                'text': '\n\n'.join(para_group),
                'strategy': 'paragraph_2',
                'doc_id': doc_id,
                'chunk_id': f"para2_{i//2}",
                'start_pos': 0,
                'end_pos': len('\n\n'.join(para_group))
            })

    # 4 paragraphs per chunk
    for i in range(0, len(paragraphs), 4):
        para_group = paragraphs[i:i+4]
        if para_group:
            chunks_by_strategy['paragraph_4'].append({
                'text': '\n\n'.join(para_group),
                'strategy': 'paragraph_4',
                'doc_id': doc_id,
                'chunk_id': f"para4_{i//4}",
                'start_pos': 0,
                'end_pos': len('\n\n'.join(para_group))
            })

    return chunks_by_strategy

def main():
    """Run simple semantic evaluation"""
    print("=== SIMPLE SEMANTIC CHUNKING EVALUATION ===")

    # Check for test files
    test_files = []

    # Check different possible locations for data
    possible_dirs = [
        Path("data/test_subset"),
        Path("newdata"),
        Path("../newdata"),
        Path("/Users/jimclifford/Library/CloudStorage/Dropbox/2025/results/newdata")
    ]

    for test_dir in possible_dirs:
        if test_dir.exists():
            json_files = list(test_dir.glob("*.json"))
            if json_files:
                test_files = json_files[:3]  # Test on first 3 files
                print(f"Found {len(json_files)} files in {test_dir}, testing on first 3")
                break

    if not test_files:
        print("No JSON test files found. Using default test subset...")
        test_files = [Path("data/test_subset/3200801612.json")]

    evaluator = SimpleSemanticEvaluator()
    all_results = {}

    for test_file in test_files:
        if not test_file.exists():
            print(f"File not found: {test_file}")
            continue

        print(f"\nAnalyzing {test_file.name}...")

        # Create chunks using different strategies
        chunks_by_strategy = create_test_chunks_from_file(test_file)

        print(f"Created chunks:")
        for strategy, chunks in chunks_by_strategy.items():
            print(f"  {strategy}: {len(chunks)} chunks")

        # Analyze semantic coherence
        results = evaluator.analyze_strategy_coherence(chunks_by_strategy)
        all_results[test_file.name] = results

        # Print results for this file
        print(f"\nResults for {test_file.name}:")
        print("-" * 50)

        for strategy, result in results.items():
            print(f"\n{strategy.upper()}:")
            print(f"  Chunks: {result['chunk_count']}")
            print(f"  Avg length: {result['avg_chunk_length']:.0f} chars")
            print(f"  Topical coherence: {result['topical_coherence']['coherence_score']:.3f}")
            print(f"  Transition similarity: {result['transition_analysis']['avg_transition_similarity']:.3f}")
            print(f"  Topic breaks detected: {result['transition_analysis']['topic_breaks_detected']}")
            print(f"  Overall score: {result['overall_score']:.3f}")
            print(f"  Top keywords: {', '.join(result['top_keywords'][:8])}")

    # Overall comparison
    print(f"\n{'='*60}")
    print("OVERALL STRATEGY COMPARISON")
    print(f"{'='*60}")

    # Aggregate results across all files
    strategy_averages = {}

    for file_results in all_results.values():
        for strategy, result in file_results.items():
            if strategy not in strategy_averages:
                strategy_averages[strategy] = []
            strategy_averages[strategy].append(result['overall_score'])

    print(f"\n{'Strategy':<20} {'Avg Score':<12} {'Files Tested':<12}")
    print("-" * 45)

    for strategy, scores in strategy_averages.items():
        avg_score = sum(scores) / len(scores)
        print(f"{strategy:<20} {avg_score:<12.3f} {len(scores):<12}")

    # Save detailed results
    output_file = "simple_semantic_results.json"
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2)

    print(f"\nDetailed results saved to {output_file}")

if __name__ == "__main__":
    main()