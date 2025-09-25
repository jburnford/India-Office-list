#!/usr/bin/env python3
"""
Test colony transition detection patterns based on meta-analysis.

Key findings from Colonial Office List analysis:
1. Colony sections end with "Foreign Consuls" lists
2. New colonies start with ALL-CAPS headers + "Situation and Area"
3. Geographic name flood after personnel sections indicates transitions
4. Pattern holds for major colonies (Hong Kong, Jamaica, Ceylon) and minor ones
"""

import re
from typing import List, Tuple, Dict
from dataclasses import dataclass

@dataclass
class TransitionSignal:
    position: int
    signal_type: str
    confidence: float
    context: str

class ColonyTransitionDetector:
    def __init__(self):
        # End-of-colony signals
        self.consular_patterns = [
            r'Foreign Consuls\.',
            r'Consuls\.',
            r'Vice-Consuls and Consular Agents\.',
        ]

        # Start-of-new-colony signals
        self.colony_headers = [
            r'^[A-Z][A-Z\s]+\.$',  # ALL CAPS with period
            r'^THE [A-Z][A-Z\s]+\.$',  # THE + ALL CAPS
        ]

        self.situation_area_pattern = r'Situation and Area\.'

        # Geographic flood indicators
        self.geographic_keywords = {
            'coordinates': r'\d+°\s*\d+\'.*?[NS].*?lat|longitude|long\.',
            'directions': r'\bmiles?\s+(north|south|east|west|from)',
            'water_bodies': r'\b(ocean|sea|river|strait|bay|harbor|harbour)\b',
            'places': r'\b(island|colony|territory|province|district)\b',
            'boundaries': r'\bbounded\s+by\b|\bbetween\b.*?\band\b'
        }

    def count_geographic_density(self, text: str, window_size: int = 500) -> float:
        """Count geographic references per character window"""
        total_matches = 0
        for pattern in self.geographic_keywords.values():
            total_matches += len(re.findall(pattern, text, re.IGNORECASE))

        return total_matches / len(text) if text else 0

    def detect_consular_end(self, text: str) -> List[TransitionSignal]:
        """Detect end of colony via consular sections"""
        signals = []

        for pattern in self.consular_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                signals.append(TransitionSignal(
                    position=match.start(),
                    signal_type="consular_end",
                    confidence=0.8,
                    context=text[max(0, match.start()-50):match.end()+50]
                ))

        return signals

    def detect_colony_start(self, text: str) -> List[TransitionSignal]:
        """Detect start of new colony via headers + geographic content"""
        signals = []

        lines = text.split('\n')

        for i, line in enumerate(lines):
            line = line.strip()

            # Check for ALL-CAPS colony headers
            for pattern in self.colony_headers:
                if re.match(pattern, line):
                    # Look ahead for "Situation and Area"
                    next_lines = '\n'.join(lines[i:i+10])

                    if re.search(self.situation_area_pattern, next_lines):
                        # Calculate geographic density in following text
                        following_text = '\n'.join(lines[i:i+20])
                        geo_density = self.count_geographic_density(following_text)

                        confidence = 0.9 if geo_density > 0.02 else 0.6

                        signals.append(TransitionSignal(
                            position=text.find(line),
                            signal_type="colony_start",
                            confidence=confidence,
                            context=f"Header: {line}\nGeo density: {geo_density:.4f}"
                        ))

        return signals

    def detect_transitions(self, text: str) -> Dict[str, List[TransitionSignal]]:
        """Detect all colony transition signals"""

        consular_ends = self.detect_consular_end(text)
        colony_starts = self.detect_colony_start(text)

        return {
            'colony_ends': consular_ends,
            'colony_starts': colony_starts
        }

    def find_transition_boundaries(self, text: str, max_gap: int = 2000) -> List[Tuple[int, int, str]]:
        """Find colony boundaries by pairing end/start signals"""

        all_signals = self.detect_transitions(text)
        boundaries = []

        ends = all_signals['colony_ends']
        starts = all_signals['colony_starts']

        # Pair each consular end with the next colony start
        for end_signal in ends:
            # Find next colony start within reasonable distance
            next_start = None
            min_distance = float('inf')

            for start_signal in starts:
                if start_signal.position > end_signal.position:
                    distance = start_signal.position - end_signal.position
                    if distance < max_gap and distance < min_distance:
                        min_distance = distance
                        next_start = start_signal

            if next_start:
                boundaries.append((
                    end_signal.position,
                    next_start.position,
                    f"Colony transition (gap: {min_distance} chars)"
                ))

        return boundaries


def test_with_sample_text():
    """Test with the sample text from user"""

    sample_text = """Congo Free State, Netherlands, consul, J. H. Batly.

HONG KONG.

Situation and Area.

Hong Kong is one of a number of islands situated off the south-eastern coast of China, at the mouth of the Canton River, and lies about 40 miles east of Macao, 91 miles south of Canton, between 22° 9' and 22° 17' N. lat., and 114° 5' and 114° 18' E. long. The island is an irregular ridge, stretching nearly east and west; its broken and abrupt peaks rising to the height of nearly 2,000 feet above the sea level."""

    detector = ColonyTransitionDetector()

    print("=== COLONY TRANSITION DETECTION TEST ===")
    print(f"Sample text length: {len(sample_text)} characters")
    print()

    # Test individual components
    signals = detector.detect_transitions(sample_text)

    print("Colony End Signals:")
    for signal in signals['colony_ends']:
        print(f"  Position {signal.position}: {signal.signal_type} (confidence: {signal.confidence})")
        print(f"  Context: {signal.context}")
        print()

    print("Colony Start Signals:")
    for signal in signals['colony_starts']:
        print(f"  Position {signal.position}: {signal.signal_type} (confidence: {signal.confidence})")
        print(f"  Context: {signal.context}")
        print()

    # Test boundary detection
    boundaries = detector.find_transition_boundaries(sample_text)
    print("Detected Boundaries:")
    for start, end, description in boundaries:
        print(f"  {start} -> {end}: {description}")
        transition_text = sample_text[start:end]
        print(f"  Transition text: {transition_text[:100]}...")
        print()

def test_with_multiple_transitions():
    """Test with text containing multiple colony transitions"""

    multi_text = """Foreign Consuls.

Germany, Holland, J. A. de Veer, consular agent, Elmina.
United States of America, consular agent, G. E. Emisang.

HONG KONG.

Situation and Area.

Hong Kong is one of a number of islands situated off the south-eastern coast of China, between 22° 9' and 22° 17' N. lat., and 114° 5' and 114° 18' E. long.

Foreign Consuls.

Austria, J. Kramer, acting consul.
Belgium, J. J. Heemskirk, consul.

JAMAICA.

Situation and Area.

Jamaica is an island in the Caribbean Sea, to the southward of the eastern extremity of the Island of Cuba, within N. lat. 17° 43' and 18° 32', and W. long. 76° 10' and 78° 20'."""

    detector = ColonyTransitionDetector()
    boundaries = detector.find_transition_boundaries(multi_text)

    print("=== MULTIPLE TRANSITIONS TEST ===")
    print(f"Found {len(boundaries)} transitions")

    for i, (start, end, desc) in enumerate(boundaries):
        print(f"Transition {i+1}: {desc}")
        transition_segment = multi_text[start:end]
        print(f"Text: {transition_segment.strip()}")
        print("-" * 50)

if __name__ == "__main__":
    test_with_sample_text()
    print("\n" + "="*60 + "\n")
    test_with_multiple_transitions()