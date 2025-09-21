#!/usr/bin/env python3
"""
Dominion-aware hierarchical extractor that properly groups provinces under dominions
"""

import json
import re
from typing import List, Dict, Tuple, Optional

class DominionAwareExtractor:
    def __init__(self):
        # Known dominions and their provinces/states
        self.dominion_structure = {
            'DOMINION OF CANADA': {
                'provinces': [
                    'ONTARIO', 'QUEBEC', 'NOVA SCOTIA', 'NEW BRUNSWICK',
                    'MANITOBA', 'ALBERTA', 'SASKATCHEWAN', 'BRITISH COLUMBIA',
                    'PRINCE EDWARD ISLAND', 'NORTHWEST TERRITORIES'
                ],
                'admin_sections': [
                    'THE SENATE OF CANADA', 'HOUSE OF COMMONS',
                    'EXECUTIVE COUNCIL', 'PRIVY COUNCIL'
                ]
            },
            'COMMONWEALTH OF AUSTRALIA': {
                'provinces': [
                    'NEW SOUTH WALES', 'VICTORIA', 'QUEENSLAND',
                    'SOUTH AUSTRALIA', 'WESTERN AUSTRALIA', 'TASMANIA',
                    'NORTHERN TERRITORY'
                ],
                'admin_sections': [
                    'FEDERAL PARLIAMENT', 'SENATE OF AUSTRALIA'
                ]
            },
            'UNION OF SOUTH AFRICA': {
                'provinces': [
                    'CAPE COLONY', 'NATAL', 'ORANGE FREE STATE', 'TRANSVAAL'
                ],
                'admin_sections': []
            }
        }

    def find_major_colony_headers(self, text: str, start_pos: int, end_pos: int) -> List[Tuple[int, str]]:
        """Find major colony headers within the colonies section"""

        colonies_text = text[start_pos:end_pos]
        boundaries = []

        lines = colonies_text.split('\n')
        current_pos = 0

        for i, line in enumerate(lines):
            line_stripped = line.strip()

            line_start_pos = current_pos
            current_pos += len(line) + 1

            if self.is_major_colony_header(line_stripped):
                absolute_pos = start_pos + line_start_pos
                colony_name = line_stripped.replace('.', '').strip()
                boundaries.append((absolute_pos, colony_name))

        return boundaries

    def is_major_colony_header(self, line: str) -> bool:
        """Check if line is a major colony header"""

        line = line.strip()

        if not (line.isupper() and line.endswith('.')):
            return False

        if len(line) < 6:
            return False

        # Exclude obvious non-colony headers
        excludes = [
            'PART', 'SECTION', 'CHAPTER', 'NO.', 'VOL.', 'PAGE',
            'FINANCES', 'IMPORTS', 'EXPORTS', 'REVENUE', 'TRADE',
            'GOVERNMENT', 'ADMINISTRATION', 'ESTABLISHMENT',
            'EDUCATION', 'POSTAL', 'TELEGRAPH', 'RAILWAY',
            'CIVIL SERVICE', 'MILITARY', 'NAVAL', 'POLICE',
            'MEDICAL', 'JUDICIAL', 'CUSTOMS', 'HARBOR',
            'PUBLIC WORKS', 'LANDS', 'AGRICULTURE',
            'ROMAN CATHOLIC', 'ANGLICAN', 'CHURCH',
            'BANKS', 'BANKING', 'INSURANCE', 'COMPANIES'
        ]

        for exclude in excludes:
            if exclude in line:
                return False

        return True

    def group_dominion_sections(self, raw_boundaries: List[Tuple[int, str]], text: str, end_pos: int) -> List[Dict]:
        """Group province/admin sections under their parent dominions"""

        grouped_colonies = []
        i = 0

        while i < len(raw_boundaries):
            current_pos, current_name = raw_boundaries[i]

            # Check if this is a dominion header
            dominion_name = self.get_dominion_name(current_name)

            if dominion_name:
                # This is a dominion - collect all its provinces/sections
                dominion_sections = []
                j = i + 1

                # Find dominion end position
                if i < len(raw_boundaries) - 1:
                    dominion_end = raw_boundaries[i + 1][0]

                    # Look ahead to see what belongs to this dominion
                    while j < len(raw_boundaries) and raw_boundaries[j][0] < dominion_end:
                        section_pos, section_name = raw_boundaries[j]

                        if self.belongs_to_dominion(section_name, dominion_name):
                            # Calculate section end
                            if j < len(raw_boundaries) - 1:
                                section_end = raw_boundaries[j + 1][0]
                            else:
                                section_end = dominion_end

                            section_text = text[section_pos:section_end].strip()

                            dominion_sections.append({
                                'name': section_name,
                                'text': section_text,
                                'start_pos': section_pos,
                                'end_pos': section_end,
                                'size': len(section_text),
                                'type': self.classify_dominion_section(section_name, dominion_name)
                            })
                            j += 1
                        else:
                            break

                    dominion_end = raw_boundaries[j][0] if j < len(raw_boundaries) else end_pos
                else:
                    dominion_end = end_pos
                    j = len(raw_boundaries)

                # Extract dominion text
                dominion_text = text[current_pos:dominion_end].strip()

                grouped_colonies.append({
                    'name': dominion_name,
                    'text': dominion_text,
                    'start_pos': current_pos,
                    'end_pos': dominion_end,
                    'size': len(dominion_text),
                    'type': 'dominion',
                    'provinces': dominion_sections,
                    'province_count': len(dominion_sections),
                    'metadata': {
                        'chunk_preview': dominion_text[:200].replace('\n', ' '),
                        'chunk_ending': dominion_text[-200:].replace('\n', ' '),
                        'position_info': f"chars {current_pos:,}-{dominion_end:,}",
                        'is_dominion': True,
                        'province_names': [s['name'] for s in dominion_sections]
                    }
                })

                i = j
            else:
                # This is a regular colony
                if i < len(raw_boundaries) - 1:
                    colony_end = raw_boundaries[i + 1][0]
                else:
                    colony_end = end_pos

                colony_text = text[current_pos:colony_end].strip()

                # Skip very small sections
                if len(colony_text) > 5000:
                    sections = self.detect_standard_sections(colony_text)

                    grouped_colonies.append({
                        'name': current_name,
                        'text': colony_text,
                        'start_pos': current_pos,
                        'end_pos': colony_end,
                        'size': len(colony_text),
                        'type': 'colony',
                        'sections': sections,
                        'section_count': len(sections),
                        'metadata': {
                            'chunk_preview': colony_text[:200].replace('\n', ' '),
                            'chunk_ending': colony_text[-200:].replace('\n', ' '),
                            'position_info': f"chars {current_pos:,}-{colony_end:,}",
                            'has_geography': any(s['type'] == 'geography' for s in sections),
                            'has_foreign_relations': any(s['type'] == 'foreign_relations' for s in sections),
                            'is_dominion': False
                        }
                    })

                i += 1

        return grouped_colonies

    def get_dominion_name(self, header_name: str) -> Optional[str]:
        """Check if header represents a dominion"""
        for dominion in self.dominion_structure.keys():
            if dominion in header_name or any(word in header_name for word in dominion.split() if len(word) > 3):
                return dominion
        return None

    def belongs_to_dominion(self, section_name: str, dominion_name: str) -> bool:
        """Check if a section belongs to a specific dominion"""
        if dominion_name not in self.dominion_structure:
            return False

        structure = self.dominion_structure[dominion_name]

        # Check provinces
        for province in structure['provinces']:
            if province in section_name:
                return True

        # Check admin sections
        for admin_section in structure['admin_sections']:
            if admin_section in section_name:
                return True

        return False

    def classify_dominion_section(self, section_name: str, dominion_name: str) -> str:
        """Classify what type of dominion section this is"""
        structure = self.dominion_structure[dominion_name]

        for province in structure['provinces']:
            if province in section_name:
                return 'province'

        for admin_section in structure['admin_sections']:
            if admin_section in section_name:
                return 'administration'

        return 'other'

    def detect_standard_sections(self, text: str) -> List[Dict]:
        """Detect sections in standard colonies"""

        section_patterns = {
            'geography': [r'Situation and Area\.', r'Physical Features\.', r'Geography\.'],
            'history': [r'History\.', r'Historical\.', r'Discovery\.'],
            'government': [r'Government\.', r'Constitution\.', r'Administration\.', r'Executive Council\.', r'Legislative Council\.'],
            'finance': [r'Finance\.', r'Finances\.', r'Revenue\.', r'Trade\.', r'Public Debt\.'],
            'personnel': [r'Establishment\.', r'Civil Establishment\.', r'Officials\.'],
            'foreign_relations': [r'Foreign Consuls?\.', r'Consuls?\.', r'Diplomatic\.'],
            'communications': [r'Communications\.', r'Postal\.', r'Telegraph\.', r'Railway\.'],
            'industry': [r'Industry\.', r'Agriculture\.', r'Mining\.', r'Commerce\.'],
            'education': [r'Education\.', r'Schools\.', r'Public Instruction\.'],
            'military': [r'Military\.', r'Defence\.', r'Naval\.', r'Garrison\.']
        }

        lines = text.split('\n')
        sections = []
        current_section_type = 'introduction'
        current_content = []

        for line in lines:
            line_stripped = line.strip()

            detected_type = None
            for section_type, patterns in section_patterns.items():
                for pattern in patterns:
                    if re.match(pattern, line_stripped, re.IGNORECASE):
                        detected_type = section_type
                        break
                if detected_type:
                    break

            if detected_type:
                if current_content:
                    content_text = '\n'.join(current_content).strip()
                    sections.append({
                        'type': current_section_type,
                        'content': content_text,
                        'size': len(content_text)
                    })

                current_section_type = detected_type
                current_content = [line]
            else:
                current_content.append(line)

        if current_content:
            content_text = '\n'.join(current_content).strip()
            sections.append({
                'type': current_section_type,
                'content': content_text,
                'size': len(content_text)
            })

        return sections

def main():
    """Extract colonies with proper dominion grouping"""

    filename = "./extracted_json/output_a29c9429212df7959632e22b6a667fd55654a592/ColonialOfficeList1896.json"

    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)

    text = data['text']
    print(f"Processing Colonial Office List 1896 ({len(text):,} characters)")

    # Use known working boundaries
    start_pos = 210954
    end_pos = 1886549

    print(f"Colonies section: {start_pos:,} to {end_pos:,} ({end_pos-start_pos:,} chars)")

    extractor = DominionAwareExtractor()

    # Find all potential boundaries first
    raw_boundaries = extractor.find_major_colony_headers(text, start_pos, end_pos)
    print(f"Found {len(raw_boundaries)} potential colony/section headers")

    # Group sections under dominions
    grouped_colonies = extractor.group_dominion_sections(raw_boundaries, text, end_pos)

    print(f"\n=== DOMINION-AWARE EXTRACTION RESULTS ===")
    print(f"Total territories extracted: {len(grouped_colonies)}")

    dominion_count = 0
    colony_count = 0

    for i, territory in enumerate(grouped_colonies):
        if territory['type'] == 'dominion':
            dominion_count += 1
            print(f"  {i+1:2d}. {territory['name']:35s} [DOMINION] ({territory['size']:6,} chars, {territory['province_count']:2d} provinces)")

            # Show provinces
            for j, province in enumerate(territory['provinces']):
                print(f"      {j+1:2d}. {province['name']:30s} [{province['type'].upper()}] ({province['size']:6,} chars)")
        else:
            colony_count += 1
            has_geography = territory['metadata'].get('has_geography', False)
            status = "✓" if has_geography else "✗"
            print(f"  {i+1:2d}. {territory['name']:35s} [COLONY]   ({territory['size']:6,} chars, {territory['section_count']:2d} sections) {status}")

    print(f"\n=== SUMMARY ===")
    print(f"Dominions: {dominion_count}")
    print(f"Regular colonies: {colony_count}")
    print(f"Total territories: {len(grouped_colonies)}")

    # Check for Canadian provinces that should have been grouped
    ungrouped_provinces = []
    for territory in grouped_colonies:
        if territory['type'] == 'colony':
            name = territory['name']
            for dominion_name, structure in extractor.dominion_structure.items():
                for province in structure['provinces']:
                    if province in name:
                        ungrouped_provinces.append((name, dominion_name))

    if ungrouped_provinces:
        print(f"\n⚠️  UNGROUPED PROVINCES DETECTED:")
        for province, should_be_under in ungrouped_provinces:
            print(f"  - {province} (should be under {should_be_under})")
    else:
        print(f"\n✓ All provinces properly grouped under dominions")

    # Save results
    output_file = "dominion_aware_extraction.json"
    result = {
        'metadata': {
            'year': '1896',
            'total_territories': len(grouped_colonies),
            'dominions': dominion_count,
            'colonies': colony_count,
            'extraction_method': 'dominion_aware'
        },
        'territories': grouped_colonies
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\nSaved results to {output_file}")

if __name__ == "__main__":
    main()