#!/usr/bin/env python3
"""
Complete hierarchical chunker - produces colony-level chunks AND section-level sub-chunks
for RAG pipeline deployment.
"""

import json
import re
from typing import List, Dict, Tuple, Optional
from dominion_aware_extractor import DominionAwareExtractor

class CompleteHierarchicalChunker:
    def __init__(self):
        self.dominion_extractor = DominionAwareExtractor()

    def create_hierarchical_chunks(self, text: str, document_year: str = "1896") -> Dict:
        """Create complete hierarchical chunks: Level 1 (colonies) + Level 2 (sections)"""

        print(f"Creating hierarchical chunks for Colonial Office List {document_year}")

        # Use known boundaries for 1896
        start_pos = 210954
        end_pos = 1886549

        # Extract territories using dominion-aware extraction
        raw_boundaries = self.dominion_extractor.find_major_colony_headers(text, start_pos, end_pos)
        territories = self.dominion_extractor.group_dominion_sections(raw_boundaries, text, end_pos)

        # Create Level 1 chunks (territories) and Level 2 chunks (sections)
        level1_chunks = []  # Colony/dominion level
        level2_chunks = []  # Section level

        chunk_id = 1

        for territory in territories:
            # Create Level 1 chunk for territory
            level1_chunk = {
                'chunk_id': f"L1_{chunk_id:03d}",
                'level': 1,
                'type': territory['type'],
                'name': territory['name'],
                'text': territory['text'],
                'size': territory['size'],
                'start_pos': territory['start_pos'],
                'end_pos': territory['end_pos'],
                'metadata': territory['metadata'].copy()
            }

            # Add territory-specific metadata
            level1_chunk['metadata'].update({
                'document_year': document_year,
                'chunk_level': 1,
                'territory_type': territory['type']
            })

            if territory['type'] == 'dominion':
                level1_chunk['province_count'] = territory['province_count']
                level1_chunk['metadata']['province_names'] = territory['metadata']['province_names']

                # Create Level 2 chunks for provinces within dominion
                for i, province in enumerate(territory['provinces']):
                    province_sections = self.extract_sections_from_province(province['text'], province['name'])

                    # Province-level chunk
                    province_chunk = {
                        'chunk_id': f"L2_{chunk_id:03d}_{i+1:02d}",
                        'level': 2,
                        'type': 'province',
                        'name': province['name'],
                        'parent_territory': territory['name'],
                        'text': province['text'],
                        'size': province['size'],
                        'start_pos': province['start_pos'],
                        'end_pos': province['end_pos'],
                        'sections': province_sections,
                        'section_count': len(province_sections),
                        'metadata': {
                            'document_year': document_year,
                            'chunk_level': 2,
                            'parent_chunk_id': level1_chunk['chunk_id'],
                            'province_type': province['type'],
                            'chunk_preview': province['text'][:200].replace('\n', ' '),
                            'chunk_ending': province['text'][-200:].replace('\n', ' '),
                            'has_geography': any(s['type'] == 'geography' for s in province_sections),
                            'section_types': [s['type'] for s in province_sections]
                        }
                    }

                    level2_chunks.append(province_chunk)

            else:
                # Regular colony - create Level 2 chunks for sections
                sections = territory.get('sections', [])
                level1_chunk['section_count'] = len(sections)

                for i, section in enumerate(sections):
                    section_chunk = {
                        'chunk_id': f"L2_{chunk_id:03d}_{i+1:02d}",
                        'level': 2,
                        'type': 'section',
                        'name': f"{territory['name']} - {section['type'].title()}",
                        'parent_territory': territory['name'],
                        'section_type': section['type'],
                        'text': section['content'],
                        'size': section['size'],
                        'metadata': {
                            'document_year': document_year,
                            'chunk_level': 2,
                            'parent_chunk_id': level1_chunk['chunk_id'],
                            'section_type': section['type'],
                            'chunk_preview': section['content'][:200].replace('\n', ' '),
                            'chunk_ending': section['content'][-200:].replace('\n', ' ')
                        }
                    }

                    level2_chunks.append(section_chunk)

            level1_chunks.append(level1_chunk)
            chunk_id += 1

        return {
            'metadata': {
                'document_year': document_year,
                'extraction_method': 'hierarchical_dominion_aware',
                'total_level1_chunks': len(level1_chunks),
                'total_level2_chunks': len(level2_chunks),
                'dominions': len([c for c in level1_chunks if c['type'] == 'dominion']),
                'colonies': len([c for c in level1_chunks if c['type'] == 'colony']),
                'provinces': len([c for c in level2_chunks if c['type'] == 'province']),
                'sections': len([c for c in level2_chunks if c['type'] == 'section'])
            },
            'level1_chunks': level1_chunks,
            'level2_chunks': level2_chunks
        }

    def extract_sections_from_province(self, province_text: str, province_name: str) -> List[Dict]:
        """Extract sections within a province"""
        return self.dominion_extractor.detect_standard_sections(province_text)

    def save_chunks_for_rag(self, chunks_data: Dict, output_prefix: str = "hierarchical_chunks"):
        """Save chunks in RAG-ready format"""

        # Save complete hierarchical structure
        complete_file = f"{output_prefix}_complete.json"
        with open(complete_file, 'w', encoding='utf-8') as f:
            json.dump(chunks_data, f, indent=2, ensure_ascii=False)

        # Save Level 1 chunks only (for high-level retrieval)
        level1_file = f"{output_prefix}_level1.json"
        level1_data = {
            'metadata': chunks_data['metadata'],
            'chunks': chunks_data['level1_chunks']
        }
        with open(level1_file, 'w', encoding='utf-8') as f:
            json.dump(level1_data, f, indent=2, ensure_ascii=False)

        # Save Level 2 chunks only (for detailed retrieval)
        level2_file = f"{output_prefix}_level2.json"
        level2_data = {
            'metadata': chunks_data['metadata'],
            'chunks': chunks_data['level2_chunks']
        }
        with open(level2_file, 'w', encoding='utf-8') as f:
            json.dump(level2_data, f, indent=2, ensure_ascii=False)

        # Save flat format for embedding (all chunks as simple text)
        flat_file = f"{output_prefix}_flat.jsonl"
        with open(flat_file, 'w', encoding='utf-8') as f:
            # Level 1 chunks
            for chunk in chunks_data['level1_chunks']:
                flat_chunk = {
                    'id': chunk['chunk_id'],
                    'text': chunk['text'],
                    'metadata': chunk['metadata']
                }
                f.write(json.dumps(flat_chunk, ensure_ascii=False) + '\n')

            # Level 2 chunks
            for chunk in chunks_data['level2_chunks']:
                flat_chunk = {
                    'id': chunk['chunk_id'],
                    'text': chunk['text'],
                    'metadata': chunk['metadata']
                }
                f.write(json.dumps(flat_chunk, ensure_ascii=False) + '\n')

        return {
            'complete': complete_file,
            'level1': level1_file,
            'level2': level2_file,
            'flat': flat_file
        }

def main():
    """Create complete hierarchical chunks for RAG deployment"""

    filename = "./extracted_json/output_a29c9429212df7959632e22b6a667fd55654a592/ColonialOfficeList1896.json"

    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)

    text = data['text']
    print(f"Processing Colonial Office List 1896 ({len(text):,} characters)")

    chunker = CompleteHierarchicalChunker()
    chunks_data = chunker.create_hierarchical_chunks(text, "1896")

    print(f"\n=== HIERARCHICAL CHUNKING RESULTS ===")
    print(f"Level 1 chunks (territories): {chunks_data['metadata']['total_level1_chunks']}")
    print(f"  - Dominions: {chunks_data['metadata']['dominions']}")
    print(f"  - Colonies: {chunks_data['metadata']['colonies']}")
    print(f"Level 2 chunks (sections): {chunks_data['metadata']['total_level2_chunks']}")
    print(f"  - Provinces: {chunks_data['metadata']['provinces']}")
    print(f"  - Colony sections: {chunks_data['metadata']['sections']}")

    # Show sample Level 1 chunks
    print(f"\n=== SAMPLE LEVEL 1 CHUNKS ===")
    for i, chunk in enumerate(chunks_data['level1_chunks'][:5]):
        territory_type = chunk['type'].upper()
        size_info = f"({chunk['size']:,} chars)"

        if chunk['type'] == 'dominion':
            province_info = f", {chunk['province_count']} provinces"
        else:
            section_info = f", {chunk['section_count']} sections"
            province_info = section_info

        print(f"  {chunk['chunk_id']}: {chunk['name']} [{territory_type}] {size_info}{province_info}")

    # Show sample Level 2 chunks
    print(f"\n=== SAMPLE LEVEL 2 CHUNKS ===")
    for i, chunk in enumerate(chunks_data['level2_chunks'][:10]):
        chunk_type = chunk['type'].upper()
        size_info = f"({chunk['size']:,} chars)"
        parent = chunk['parent_territory']

        print(f"  {chunk['chunk_id']}: {chunk['name']} [{chunk_type}] {size_info}")
        print(f"            Parent: {parent}")

    # Save in multiple formats for RAG
    output_files = chunker.save_chunks_for_rag(chunks_data, "colonial_office_1896")

    print(f"\n=== OUTPUT FILES FOR RAG ===")
    for format_name, filename in output_files.items():
        print(f"  {format_name.upper()}: {filename}")

    # Show deployment recommendations
    print(f"\n=== RAG DEPLOYMENT RECOMMENDATIONS ===")
    print(f"For territory-level retrieval: Use {output_files['level1']}")
    print(f"For detailed section retrieval: Use {output_files['level2']}")
    print(f"For embedding pipeline: Use {output_files['flat']}")
    print(f"For complete structure: Use {output_files['complete']}")

    # Calculate chunk size statistics
    level1_sizes = [chunk['size'] for chunk in chunks_data['level1_chunks']]
    level2_sizes = [chunk['size'] for chunk in chunks_data['level2_chunks']]

    print(f"\n=== CHUNK SIZE STATISTICS ===")
    if level1_sizes:
        print(f"Level 1 (territories): min={min(level1_sizes):,}, max={max(level1_sizes):,}, avg={sum(level1_sizes)//len(level1_sizes):,}")
    if level2_sizes:
        print(f"Level 2 (sections): min={min(level2_sizes):,}, max={max(level2_sizes):,}, avg={sum(level2_sizes)//len(level2_sizes):,}")

if __name__ == "__main__":
    main()