"""
Embedding-based Colony Section Detector

Uses semantic embeddings to identify colony boundaries in the Colonial Office List.
This approach is more robust than rule-based pattern matching for semi-structured
historical documents with irregular patterns.
"""

import json
import numpy as np
from typing import List, Dict, Tuple, Optional
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import DBSCAN
import matplotlib.pyplot as plt

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("Warning: sentence-transformers not available. Install with: pip install sentence-transformers")

class EmbeddingColonyDetector:
    """
    Detects colony section boundaries using semantic embeddings.

    The approach:
    1. Generate embeddings for each chunk
    2. Calculate semantic similarity between consecutive chunks
    3. Detect significant drops in similarity as section boundaries
    4. Use clustering to group chunks by semantic similarity
    """

    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initialize with a sentence transformer model.

        Args:
            model_name: Name of the sentence transformer model to use
        """
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError("sentence-transformers library required. Install with: pip install sentence-transformers")

        self.model = SentenceTransformer(model_name)
        self.embeddings = None
        self.chunks = None

    def generate_embeddings(self, chunks: List[Dict]) -> np.ndarray:
        """
        Generate embeddings for all chunks.

        Args:
            chunks: List of chunk dictionaries with 'text' field

        Returns:
            numpy array of embeddings [n_chunks, embedding_dim]
        """
        self.chunks = chunks

        # Extract text and create meaningful representations for embedding
        texts = []
        for chunk in chunks:
            text = chunk['text']

            # Take first 500 chars to focus on the beginning (often contains section headers)
            # This helps identify colony headers and administrative structure changes
            representative_text = text[:500]
            texts.append(representative_text)

        print(f"Generating embeddings for {len(texts)} chunks...")
        self.embeddings = self.model.encode(texts, show_progress_bar=True)

        return self.embeddings

    def detect_semantic_boundaries(self,
                                  similarity_threshold: float = 0.7,
                                  window_size: int = 3) -> List[Tuple[int, float]]:
        """
        Detect section boundaries based on semantic similarity drops.

        Args:
            similarity_threshold: Threshold below which we consider a boundary
            window_size: Size of rolling window for similarity calculation

        Returns:
            List of (chunk_index, similarity_score) for detected boundaries
        """
        if self.embeddings is None:
            raise ValueError("Must generate embeddings first")

        boundaries = []

        # Calculate rolling average similarity
        for i in range(window_size, len(self.embeddings) - window_size):
            # Compare current window with next window
            current_window = self.embeddings[i-window_size:i]
            next_window = self.embeddings[i:i+window_size]

            # Calculate average similarity between windows
            similarities = []
            for curr_emb in current_window:
                for next_emb in next_window:
                    sim = cosine_similarity([curr_emb], [next_emb])[0][0]
                    similarities.append(sim)

            avg_similarity = np.mean(similarities)

            # If similarity drops significantly, this might be a boundary
            if avg_similarity < similarity_threshold:
                boundaries.append((i, avg_similarity))

        return boundaries

    def cluster_by_content_type(self, n_clusters: int = None) -> Dict[int, int]:
        """
        Cluster chunks by semantic similarity to identify content types.

        Args:
            n_clusters: Number of clusters (if None, use DBSCAN for automatic detection)

        Returns:
            Dictionary mapping chunk_index -> cluster_id
        """
        if self.embeddings is None:
            raise ValueError("Must generate embeddings first")

        if n_clusters is None:
            # Use DBSCAN for automatic cluster detection
            clustering = DBSCAN(eps=0.3, min_samples=5, metric='cosine')
            cluster_labels = clustering.fit_predict(self.embeddings)
        else:
            from sklearn.cluster import KMeans
            clustering = KMeans(n_clusters=n_clusters, random_state=42)
            cluster_labels = clustering.fit_predict(self.embeddings)

        return {i: label for i, label in enumerate(cluster_labels)}

    def find_colony_sections(self,
                           known_colonies: List[str] = None,
                           similarity_threshold: float = 0.6) -> Dict[str, List[int]]:
        """
        Find sections for specific colonies using embedding similarity.

        Args:
            known_colonies: List of colony names to search for
            similarity_threshold: Threshold for considering chunks as part of same colony

        Returns:
            Dictionary mapping colony_name -> list of chunk indices
        """
        if known_colonies is None:
            known_colonies = [
                "Gold Coast", "Sierra Leone", "Lagos", "Gambia",
                "Jamaica", "British Honduras", "Cyprus", "Malta",
                "Ceylon", "Straits Settlements", "Hong Kong"
            ]

        colony_sections = {}

        for colony in known_colonies:
            print(f"Searching for {colony} section...")

            # Find chunks that mention the colony
            colony_chunks = []
            for i, chunk in enumerate(self.chunks):
                if colony.lower() in chunk['text'].lower():
                    colony_chunks.append(i)

            if not colony_chunks:
                continue

            # Find the most likely "header" chunk (often contains "THE [COLONY] COLONY")
            header_candidates = []
            for idx in colony_chunks:
                text = self.chunks[idx]['text']
                if (f"THE {colony.upper()}" in text.upper() or
                    f"{colony.upper()} COLONY" in text.upper()):
                    header_candidates.append(idx)

            if not header_candidates:
                # Fallback to first mention
                header_candidates = [colony_chunks[0]]

            # Use the first header candidate as anchor
            anchor_idx = header_candidates[0]
            anchor_embedding = self.embeddings[anchor_idx]

            # Find all chunks semantically similar to the anchor
            section_chunks = [anchor_idx]

            # Look forward and backward from anchor
            for direction in [1, -1]:
                current_idx = anchor_idx

                while True:
                    next_idx = current_idx + direction

                    if next_idx < 0 or next_idx >= len(self.embeddings):
                        break

                    # Calculate similarity to anchor
                    similarity = cosine_similarity([anchor_embedding],
                                                 [self.embeddings[next_idx]])[0][0]

                    if similarity > similarity_threshold:
                        section_chunks.append(next_idx)
                        current_idx = next_idx
                    else:
                        # Also check if this chunk mentions the colony
                        if colony.lower() in self.chunks[next_idx]['text'].lower():
                            section_chunks.append(next_idx)
                            current_idx = next_idx
                        else:
                            break

            colony_sections[colony] = sorted(list(set(section_chunks)))

        return colony_sections

    def visualize_similarity_profile(self, start_idx: int = 0, end_idx: int = 100):
        """
        Visualize the semantic similarity profile to help identify boundaries.

        Args:
            start_idx: Start chunk index for visualization
            end_idx: End chunk index for visualization
        """
        if self.embeddings is None:
            raise ValueError("Must generate embeddings first")

        # Calculate consecutive similarities
        similarities = []
        for i in range(start_idx, min(end_idx - 1, len(self.embeddings) - 1)):
            sim = cosine_similarity([self.embeddings[i]], [self.embeddings[i + 1]])[0][0]
            similarities.append(sim)

        plt.figure(figsize=(15, 8))
        plt.plot(range(start_idx, start_idx + len(similarities)), similarities, 'b-', alpha=0.7)
        plt.axhline(y=0.7, color='r', linestyle='--', alpha=0.5, label='Potential boundary threshold')
        plt.xlabel('Chunk Index')
        plt.ylabel('Cosine Similarity')
        plt.title('Semantic Similarity Between Consecutive Chunks')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.show()

        # Identify potential boundaries
        low_similarity_points = []
        for i, sim in enumerate(similarities):
            if sim < 0.7:  # Threshold for potential boundary
                low_similarity_points.append((start_idx + i, sim))

        print(f"Potential section boundaries (similarity < 0.7):")
        for idx, sim in low_similarity_points[:10]:  # Show top 10
            chunk_preview = self.chunks[idx]['text'][:100]
            print(f"  Chunk {idx} (sim: {sim:.3f}): {chunk_preview}...")

        return similarities, low_similarity_points


def demo_embedding_colony_detection():
    """Demo function showing how to use the embedding-based colony detector."""

    print("🔍 Embedding-based Colony Section Detection Demo")
    print("=" * 60)

    # Load chunking results
    try:
        with open('chunking_test_results.json', 'r', encoding='utf-8') as f:
            results = json.load(f)
    except FileNotFoundError:
        print("❌ chunking_test_results.json not found. Run test_adaptive_chunking.py first.")
        return

    # Get Colonial Office List chunks
    colonial_office_result = None
    for result in results['results']:
        if (result['document_profile']['document_type'] == 'administrative' and
            result['total_chars'] > 1000000):
            colonial_office_result = result
            break

    if not colonial_office_result:
        print("❌ Could not find Colonial Office List in results")
        return

    chunks = colonial_office_result['chunks']
    print(f"📊 Loaded {len(chunks)} chunks from Colonial Office List")

    # Initialize detector
    if not SENTENCE_TRANSFORMERS_AVAILABLE:
        print("❌ sentence-transformers not available. Install with: pip install sentence-transformers")
        return

    detector = EmbeddingColonyDetector()

    # Work with a subset for demonstration (full document would take longer)
    subset_chunks = chunks[900:1100]  # Around Gold Coast area
    print(f"🔬 Working with subset: chunks 900-1100 ({len(subset_chunks)} chunks)")

    # Generate embeddings
    embeddings = detector.generate_embeddings(subset_chunks)
    print(f"✅ Generated embeddings: {embeddings.shape}")

    # Find colony sections
    colony_sections = detector.find_colony_sections([
        "Gold Coast", "Sierra Leone", "Lagos", "Jamaica"
    ])

    print(f"\n🏛️ COLONY SECTIONS DETECTED:")
    print("-" * 40)
    for colony, chunk_indices in colony_sections.items():
        if chunk_indices:
            print(f"\n📍 {colony}:")
            print(f"   Chunks: {len(chunk_indices)} (indices: {chunk_indices[:5]}{'...' if len(chunk_indices) > 5 else ''})")

            # Show sample content
            first_chunk = subset_chunks[chunk_indices[0]]
            preview = first_chunk['text'][:200]
            print(f"   Preview: {preview}...")

    # Detect semantic boundaries
    boundaries = detector.detect_semantic_boundaries(similarity_threshold=0.6)
    print(f"\n🔍 SEMANTIC BOUNDARIES DETECTED:")
    print("-" * 40)
    for chunk_idx, similarity in boundaries[:5]:  # Show first 5
        chunk_preview = subset_chunks[chunk_idx]['text'][:100]
        print(f"   Boundary at chunk {chunk_idx + 900} (similarity: {similarity:.3f})")
        print(f"   Content: {chunk_preview}...")
        print()

    return detector, colony_sections, boundaries


if __name__ == "__main__":
    demo_embedding_colony_detection()