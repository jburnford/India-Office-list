#!/usr/bin/env python3
"""
Comprehensive test suite for the improved hierarchical extractor
================================================================

Tests the key improvements:
1. Canadian provinces grouped under Dominion of Canada
2. Administrative sections filtered out
3. Duplicate territories resolved
4. Content validation working properly
"""

import json
from typing import Dict, List
from improved_hierarchical_extractor import (
    ImprovedHierarchicalExtractor,
    HeaderClassifier,
    HeaderType
)

class ExtractorTester:
    def __init__(self):
        self.extractor = ImprovedHierarchicalExtractor()
        self.classifier = HeaderClassifier()

    def run_comprehensive_tests(self, text: str) -> Dict:
        """Run all tests and return detailed results"""

        print("=" * 60)
        print("COMPREHENSIVE EXTRACTOR TESTING")
        print("=" * 60)

        # Extract using improved method
        result = self.extractor.extract(text, "1896")

        test_results = {
            'canadian_grouping': self.test_canadian_province_grouping(result),
            'administrative_filtering': self.test_administrative_filtering(result),
            'duplicate_resolution': self.test_duplicate_resolution(result),
            'content_validation': self.test_content_validation(result),
            'hierarchy_structure': self.test_hierarchy_structure(result),
            'boundary_accuracy': self.test_boundary_accuracy(result),
            'classification_accuracy': self.test_classification_accuracy(text),
            'overall_metrics': self.calculate_overall_metrics(result)
        }

        self.print_test_summary(test_results)
        return test_results

    def test_canadian_province_grouping(self, result: Dict) -> Dict:
        """Test that Canadian provinces are properly grouped under Dominion of Canada"""

        print("\n🇨🇦 Testing Canadian Province Grouping...")

        # Find Dominion of Canada
        canada_chunks = [c for c in result['level1_chunks'] if 'CANADA' in c['name']]

        if not canada_chunks:
            return {
                'passed': False,
                'error': 'Dominion of Canada not found in level 1 chunks',
                'expected_provinces': 0,
                'found_provinces': 0
            }

        canada = canada_chunks[0]

        # Check that it's classified as dominion
        if canada['type'] != 'dominion':
            return {
                'passed': False,
                'error': f"Canada classified as {canada['type']}, expected 'dominion'",
                'expected_provinces': 0,
                'found_provinces': 0
            }

        # Count provinces under Canada
        canadian_level2 = [c for c in result['level2_chunks']
                          if c.get('parent_territory') == canada['name']]

        # Check for ungrouped provinces in level 1
        canadian_provinces = {"ONTARIO", "QUEBEC", "NOVA SCOTIA", "NEW BRUNSWICK",
                            "MANITOBA", "BRITISH COLUMBIA", "PRINCE EDWARD ISLAND"}

        ungrouped_provinces = []
        for chunk in result['level1_chunks']:
            if any(province in chunk['name'] for province in canadian_provinces):
                ungrouped_provinces.append(chunk['name'])

        provinces_found = len(canadian_level2)
        expected_min = 4  # At least Ontario, Quebec, Nova Scotia, New Brunswick

        passed = (provinces_found >= expected_min and len(ungrouped_provinces) == 0)

        print(f"  ✓ Canada found as dominion: {canada['name']}")
        print(f"  ✓ Provinces under Canada: {provinces_found}")
        print(f"  ✓ Ungrouped provinces: {len(ungrouped_provinces)}")
        if ungrouped_provinces:
            print(f"    Ungrouped: {ungrouped_provinces}")

        return {
            'passed': passed,
            'canada_found': True,
            'canada_type': canada['type'],
            'provinces_under_canada': provinces_found,
            'expected_min_provinces': expected_min,
            'ungrouped_provinces': ungrouped_provinces,
            'level2_provinces': [c['name'] for c in canadian_level2]
        }

    def test_administrative_filtering(self, result: Dict) -> Dict:
        """Test that administrative sections are filtered out"""

        print("\n🏛️ Testing Administrative Section Filtering...")

        administrative_terms = [
            'SENATE OF CANADA', 'EXECUTIVE COUNCIL', 'LEGISLATIVE COUNCIL',
            'PRIME MINISTER', 'ECCLESIASTICAL', 'BISHOPS', 'CIVIL SERVICE'
        ]

        # Check level 1 chunks for administrative sections
        admin_in_level1 = []
        for chunk in result['level1_chunks']:
            if any(term in chunk['name'] for term in administrative_terms):
                admin_in_level1.append(chunk['name'])

        # This should be empty or very small
        passed = len(admin_in_level1) <= 1  # Allow one possible edge case

        print(f"  ✓ Administrative sections in Level 1: {len(admin_in_level1)}")
        if admin_in_level1:
            print(f"    Found: {admin_in_level1}")

        return {
            'passed': passed,
            'admin_sections_in_level1': len(admin_in_level1),
            'admin_sections_found': admin_in_level1
        }

    def test_duplicate_resolution(self, result: Dict) -> Dict:
        """Test that duplicate territories are resolved"""

        print("\n🔍 Testing Duplicate Resolution...")

        # Check for duplicates by name similarity
        level1_names = [c['name'] for c in result['level1_chunks']]

        # Normalize names and check for duplicates
        normalized_names = []
        for name in level1_names:
            normalized = ''.join(c for c in name.upper() if c.isalnum())
            normalized_names.append(normalized)

        unique_normalized = set(normalized_names)
        duplicate_count = len(normalized_names) - len(unique_normalized)

        # Check for known problematic duplicates
        known_duplicates = ['CEYLON', 'EASTERN PROVINCE']
        found_duplicates = []

        for duplicate in known_duplicates:
            count = sum(1 for name in level1_names if duplicate in name)
            if count > 1:
                found_duplicates.append(f"{duplicate} ({count} times)")

        passed = duplicate_count == 0 and len(found_duplicates) == 0

        print(f"  ✓ Total duplicates found: {duplicate_count}")
        print(f"  ✓ Known problematic duplicates: {len(found_duplicates)}")
        if found_duplicates:
            print(f"    Found: {found_duplicates}")

        return {
            'passed': passed,
            'total_duplicates': duplicate_count,
            'known_duplicates_found': found_duplicates,
            'unique_territories': len(unique_normalized)
        }

    def test_content_validation(self, result: Dict) -> Dict:
        """Test that content validation is working"""

        print("\n📋 Testing Content Validation...")

        # Check that territories have reasonable sizes
        level1_sizes = [c['size'] for c in result['level1_chunks']]

        min_size = min(level1_sizes) if level1_sizes else 0
        max_size = max(level1_sizes) if level1_sizes else 0
        avg_size = sum(level1_sizes) // len(level1_sizes) if level1_sizes else 0

        # Check geographic content
        with_geography = 0
        for chunk in result['level1_chunks']:
            if chunk['metadata'].get('has_geography', False):
                with_geography += 1

        geography_percentage = (with_geography / len(result['level1_chunks']) * 100) if result['level1_chunks'] else 0

        # Validation criteria
        size_validation = min_size > 1000  # Minimum reasonable territory size
        geography_validation = geography_percentage > 30  # Reasonable geographic content

        passed = size_validation and geography_validation

        print(f"  ✓ Territory sizes: min={min_size:,}, max={max_size:,}, avg={avg_size:,}")
        print(f"  ✓ Territories with geography: {with_geography}/{len(result['level1_chunks'])} ({geography_percentage:.1f}%)")

        return {
            'passed': passed,
            'min_size': min_size,
            'max_size': max_size,
            'avg_size': avg_size,
            'with_geography': with_geography,
            'geography_percentage': geography_percentage,
            'size_validation': size_validation,
            'geography_validation': geography_validation
        }

    def test_hierarchy_structure(self, result: Dict) -> Dict:
        """Test that hierarchy structure is correct"""

        print("\n🏗️ Testing Hierarchy Structure...")

        # Check that all level 2 chunks have valid parents
        orphaned_level2 = []
        level1_names = [c['name'] for c in result['level1_chunks']]

        for chunk in result['level2_chunks']:
            parent = chunk.get('parent_territory')
            if parent not in level1_names:
                orphaned_level2.append(chunk['name'])

        # Check that dominions have level 2 subdivisions
        dominions = [c for c in result['level1_chunks'] if c['type'] == 'dominion']
        dominions_with_subdivisions = 0

        for dominion in dominions:
            level2_for_dominion = [c for c in result['level2_chunks']
                                 if c.get('parent_territory') == dominion['name']]
            if level2_for_dominion:
                dominions_with_subdivisions += 1

        hierarchy_validation = (len(orphaned_level2) == 0 and
                              dominions_with_subdivisions == len(dominions))

        passed = hierarchy_validation

        print(f"  ✓ Level 1 chunks: {len(result['level1_chunks'])}")
        print(f"  ✓ Level 2 chunks: {len(result['level2_chunks'])}")
        print(f"  ✓ Orphaned level 2 chunks: {len(orphaned_level2)}")
        print(f"  ✓ Dominions with subdivisions: {dominions_with_subdivisions}/{len(dominions)}")

        return {
            'passed': passed,
            'level1_count': len(result['level1_chunks']),
            'level2_count': len(result['level2_chunks']),
            'orphaned_level2': orphaned_level2,
            'dominions_with_subdivisions': dominions_with_subdivisions,
            'total_dominions': len(dominions)
        }

    def test_boundary_accuracy(self, result: Dict) -> Dict:
        """Test boundary detection accuracy"""

        print("\n🎯 Testing Boundary Accuracy...")

        # Check for known good extractions from the original document
        known_good_territories = [
            'BASUTOLAND', 'BERMUDA', 'BRITISH GUIANA', 'BRITISH HONDURAS',
            'GIBRALTAR', 'JAMAICA', 'MAURITIUS', 'HONG KONG'
        ]

        found_good_territories = 0
        level1_names = [c['name'] for c in result['level1_chunks']]

        for territory in known_good_territories:
            if any(territory in name for name in level1_names):
                found_good_territories += 1

        accuracy_percentage = (found_good_territories / len(known_good_territories) * 100)
        passed = accuracy_percentage >= 70  # Should find most known good territories

        print(f"  ✓ Known good territories found: {found_good_territories}/{len(known_good_territories)} ({accuracy_percentage:.1f}%)")

        return {
            'passed': passed,
            'known_good_found': found_good_territories,
            'known_good_total': len(known_good_territories),
            'accuracy_percentage': accuracy_percentage
        }

    def test_classification_accuracy(self, text: str) -> Dict:
        """Test header classification accuracy"""

        print("\n🏷️ Testing Header Classification...")

        # Test specific headers
        test_headers = [
            ("DOMINION OF CANADA", HeaderType.DOMINION),
            ("ONTARIO", HeaderType.PROVINCE),
            ("HONG KONG", HeaderType.CROWN_COLONY),
            ("SENATE OF CANADA", HeaderType.ADMINISTRATIVE),
            ("BRITISH GUIANA", HeaderType.CROWN_COLONY)
        ]

        correct_classifications = 0
        classification_results = []

        for header_text, expected_type in test_headers:
            # Mock context for testing
            from improved_hierarchical_extractor import ParseContext
            context = ParseContext()

            if expected_type == HeaderType.PROVINCE:
                context.current_dominion = "DOMINION OF CANADA"

            classified_type = self.classifier._classify_header_with_context(header_text, context)
            is_correct = classified_type == expected_type

            if is_correct:
                correct_classifications += 1

            classification_results.append({
                'header': header_text,
                'expected': expected_type.value,
                'classified': classified_type.value,
                'correct': is_correct
            })

        accuracy = (correct_classifications / len(test_headers) * 100) if test_headers else 0
        passed = accuracy >= 80

        print(f"  ✓ Classification accuracy: {correct_classifications}/{len(test_headers)} ({accuracy:.1f}%)")

        return {
            'passed': passed,
            'correct_classifications': correct_classifications,
            'total_tested': len(test_headers),
            'accuracy_percentage': accuracy,
            'detailed_results': classification_results
        }

    def calculate_overall_metrics(self, result: Dict) -> Dict:
        """Calculate overall extraction metrics"""

        print("\n📊 Calculating Overall Metrics...")

        metadata = result['metadata']

        # Efficiency metrics
        total_chunks = metadata['total_level1_chunks'] + metadata['total_level2_chunks']

        # Quality indicators
        dominion_ratio = metadata['dominions'] / metadata['total_level1_chunks'] if metadata['total_level1_chunks'] else 0

        # Size distribution
        level1_sizes = [c['size'] for c in result['level1_chunks']]
        size_distribution = {
            'min': min(level1_sizes) if level1_sizes else 0,
            'max': max(level1_sizes) if level1_sizes else 0,
            'avg': sum(level1_sizes) // len(level1_sizes) if level1_sizes else 0
        }

        print(f"  ✓ Total chunks generated: {total_chunks}")
        print(f"  ✓ Dominion ratio: {dominion_ratio:.2f}")
        print(f"  ✓ Size distribution: {size_distribution}")

        return {
            'total_chunks': total_chunks,
            'dominion_ratio': dominion_ratio,
            'size_distribution': size_distribution,
            'extraction_method': metadata['extraction_method']
        }

    def print_test_summary(self, test_results: Dict):
        """Print comprehensive test summary"""

        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)

        total_tests = len([t for t in test_results.values() if isinstance(t, dict) and 'passed' in t])
        passed_tests = len([t for t in test_results.values() if isinstance(t, dict) and t.get('passed', False)])

        print(f"\nOverall: {passed_tests}/{total_tests} tests passed ({passed_tests/total_tests*100:.1f}%)")

        print("\n📋 DETAILED RESULTS:")
        for test_name, result in test_results.items():
            if isinstance(result, dict) and 'passed' in result:
                status = "✅ PASS" if result['passed'] else "❌ FAIL"
                print(f"  {test_name.replace('_', ' ').title()}: {status}")

        print("\n🎯 KEY IMPROVEMENTS VERIFIED:")

        # Canadian grouping
        if test_results['canadian_grouping']['passed']:
            print("  ✅ Canadian provinces properly grouped under Dominion of Canada")
        else:
            print("  ❌ Canadian province grouping issue remains")

        # Administrative filtering
        if test_results['administrative_filtering']['passed']:
            print("  ✅ Administrative sections filtered out")
        else:
            print("  ❌ Administrative sections still present as territories")

        # Duplicate resolution
        if test_results['duplicate_resolution']['passed']:
            print("  ✅ Duplicate territories resolved")
        else:
            print("  ❌ Duplicate territories still present")

        return passed_tests / total_tests

def main():
    """Run comprehensive testing"""

    filename = "./extracted_json/output_a29c9429212df7959632e22b6a667fd55654a592/ColonialOfficeList1896.json"

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)

        text = data['text']
        print(f"Loaded Colonial Office List 1896 ({len(text):,} characters)")

        tester = ExtractorTester()
        test_results = tester.run_comprehensive_tests(text)

        # Save test results
        output_file = "test_results_improved_extractor.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(test_results, f, indent=2, ensure_ascii=False)

        print(f"\nTest results saved to {output_file}")

    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()