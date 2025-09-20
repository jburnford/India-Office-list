# Modern RAG Pipeline for Historical OCR Documents

## Project Overview

This project implements a state-of-the-art vector database pipeline for Retrieval-Augmented Generation (RAG) from OLM-OCR processed historical documents. The approach goes beyond basic chunking strategies to handle the unique challenges of irregular historical sources.

## Dataset Characteristics

- **Source**: OLM-OCR processed JSON files from historical documents
- **Quality**: ~5% word error rate (better than typical historical OCR)
- **Structure**: Mix of single-page and multi-page documents (1-570 pages)
- **Content**: Historical texts with irregular layouts and structures
- **Volume**: 661 JSON files ranging from 2KB to 2.8MB

## Modern RAG Architecture (2025 Best Practices)

### Phase 1: Document Structure Analysis & Preprocessing

**DocLing Integration**
- Use IBM's DocLing toolkit for advanced document structure analysis
- Preserve semantic structure rather than treating text as flat strings
- Extract logical elements: headers, paragraphs, tables, lists
- Handle irregular layouts common in historical documents

**OCR Post-Processing**
- Given 5% error rate, focus on context preservation over heavy correction
- Maintain document structure and reading order
- Preserve metadata about page boundaries and layout elements

### Phase 2: Advanced Chunking Strategies

#### A. Semantic Chunking with LLM Boundary Detection
**Approach**: "Agentic Chunking"
- Use small LLMs to identify natural breakpoints in historical text
- Understand document flow and topic transitions
- Superior to character-count or sentence-based splitting
- Handles irregular historical text structures

#### B. Max-Min Semantic Similarity Chunking
**Method**: Dynamic boundary detection
- Generate embeddings for sentences/paragraphs
- Calculate cosine similarity between consecutive segments
- Use similarity thresholds (e.g., 0.7) to detect topic shifts
- Adaptively determine chunk boundaries based on semantic coherence
- Average performance metrics: AMI scores of 0.85-0.90, accuracy of 0.56

#### C. BERTopic-Based Topic Segmentation
**Purpose**: Topic-aware document organization
- Cluster document sections by semantic topics using BERTopic
- Create metadata tags for topic-based filtering and retrieval
- Group semantically similar chunks across documents
- Particularly valuable for heterogeneous historical collections

#### D. Hybrid Overlapping Strategy (Baseline)
**Traditional approach** for comparison:
- Fixed-size chunks with configurable overlap
- Sentence-boundary optimization
- Simple to implement and understand

### Phase 3: Modern Embedding & Vector Storage

#### Embedding Models (2025 Recommendations)
1. **Jina AI embeddings**: Strong retrieval performance, optimized for search
2. **Cohere Embed v3**: Excellent domain adaptation capabilities
3. **Voyage AI**: High performance on academic/historical text
4. **Avoid**: Older OpenAI text-embedding-3 models (March 2023)

#### Vector Database Comparison
1. **ChromaDB**:
   - Best for prototyping and local development
   - Easy setup and testing
   - ~$150/month for moderate scale
2. **Qdrant**:
   - Superior real-time performance
   - Written in Rust for speed
   - Real-time updates and filtering
3. **Milvus**:
   - Enterprise-scale capabilities
   - Handles billions of vectors
   - Production-ready with clustering

### Phase 4: Hybrid Retrieval System

#### Multi-Modal Search Strategy
1. **Keyword Search (BM25)**:
   - Exact term matching for historical names, dates, places
   - Critical for factual historical queries
2. **Vector Search**:
   - Semantic similarity for conceptual queries
   - Handle synonym and paraphrase matching
3. **Reranking**:
   - Combine keyword and vector results
   - LLM-based relevance scoring (ChunkRAG approach)
   - Filter irrelevant chunks before generation

### Phase 5: Evaluation Framework

#### Chunk Quality Metrics
- **Semantic Coherence**: Topic consistency within chunks
- **Boundary Quality**: Natural breakpoints vs. arbitrary splits
- **Size Distribution**: Optimal chunk lengths for context windows

#### Retrieval Performance
- **Precision@K**: Accuracy of top-K results
- **NDCG**: Normalized Discounted Cumulative Gain
- **Query Type Analysis**: Performance on different historical query patterns

#### A/B Testing Framework
- Compare chunking strategies on representative queries
- Measure end-to-end RAG performance
- Evaluate generation quality and factual accuracy

## Implementation Strategy

### Priority Order
1. **Document Analysis**: Implement DocLing integration first
2. **Baseline Chunking**: Max-Min semantic similarity (simpler than LLM-based)
3. **Topic Clustering**: Add BERTopic for metadata enrichment
4. **Embedding Evaluation**: Test modern embedding models on subset
5. **Vector Storage**: Compare database options at scale
6. **Hybrid Retrieval**: Implement keyword + vector search
7. **Advanced Chunking**: LLM-based boundary detection
8. **Evaluation Framework**: Comprehensive testing and metrics

### Test Subset Selection
- **Diversity Focus**: Avoid multiple India Office List volumes
- **Representative Sample**: Different document types, sizes, and time periods
- **Quality Range**: Mix of clean and challenging OCR examples
- **Size Distribution**: Small, medium, and large documents

## Key Advantages Over Basic Approaches

1. **Structure-Aware**: Preserves document semantics vs. flat text splitting
2. **LLM-Enhanced**: AI understanding of content boundaries vs. character counts
3. **Topic-Aware**: Semantic clustering vs. arbitrary chunks
4. **Hybrid Search**: Combines exact matching with semantic search
5. **Modern Embeddings**: 2025 retrieval-optimized models
6. **Error-Resilient**: Handles OCR irregularities through semantic understanding

## Expected Outcomes

- Improved retrieval accuracy for historical queries
- Better handling of irregular document structures
- More coherent and contextually relevant chunks
- Robust performance across different document types
- Scalable architecture for large historical collections

## Technology Stack

- **Document Processing**: DocLing, Python
- **Chunking**: Custom implementations, sentence-transformers
- **Topic Modeling**: BERTopic, HDBSCAN
- **Embeddings**: Jina AI, Cohere, Voyage AI models
- **Vector Storage**: ChromaDB (development), Qdrant/Milvus (production)
- **Retrieval**: Custom hybrid search implementation
- **Evaluation**: Custom metrics framework

## Project Structure

```
/
├── data/
│   ├── raw/                    # Original OLM-OCR JSON files
│   ├── test_subset/           # Selected diverse test files
│   └── processed/             # Chunked and embedded data
├── src/
│   ├── preprocessing/         # DocLing integration
│   ├── chunking/             # Chunking strategies
│   ├── embedding/            # Embedding pipelines
│   ├── retrieval/            # Hybrid search system
│   └── evaluation/           # Metrics and testing
├── notebooks/                # Jupyter notebooks for exploration
├── configs/                  # Configuration files
├── tests/                    # Unit and integration tests
└── docs/                     # Additional documentation
```