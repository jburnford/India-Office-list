# Test Dataset

This directory contains a diverse subset of historical documents for testing RAG chunking strategies.

## Files Selected

### Single-Page Documents (2-5KB)
- `3200797029.json` (2.8KB) - Short historical text
- `3200801612.json` (5.2KB) - Crime report, good narrative structure
- `3200803382.json` (5.2KB) - Medium-length document
- `3207163575.json` (3.7KB) - Additional single-page sample

### Multi-Page Documents
- `iacsl_1872_jan.json` (1.9MB, ~570 pages) - Indian Army and Civil Service List, structured administrative document
- `iliol_1896.json` (2.7MB, ~570 pages) - India Office List, different administrative format

## Document Types Represented

1. **Narrative Text**: Crime reports and news articles
2. **Administrative Lists**: Military and civil service records
3. **Mixed Content**: Tables, lists, and prose combined
4. **Size Range**: 2KB to 2.7MB (1-570 pages)
5. **Time Period**: 1870s-1890s historical documents

## Selection Criteria

- **Diversity**: Avoided multiple volumes of the same publication type
- **Structure Variety**: Different document layouts and content types
- **Size Distribution**: Representative sample across file size spectrum
- **OCR Quality**: Mix of clean and challenging text for robustness testing

This subset allows comprehensive testing of chunking strategies across different historical document types while maintaining manageable computational requirements for development and evaluation.