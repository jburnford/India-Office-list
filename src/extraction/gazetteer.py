"""Location gazetteer for India Office List entities.

Manages canonical location records and maps variant spellings to canonical
forms.  Bootstrapped from known regions in the India Office Lists, then
extended incrementally as new locations are extracted.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class GazetteerEntry:
    """A canonical location record."""
    canonical: str
    location_type: str              # "region", "city", "district", "institution", "agency"
    parent_region: Optional[str] = None
    modern_name: Optional[str] = None
    variants: List[str] = field(default_factory=list)
    wikidata_id: Optional[str] = None
    geonames_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Bootstrap data — regions and major cities from the India Office Lists
# ---------------------------------------------------------------------------

_BOOTSTRAP_REGIONS: List[Dict[str, Any]] = [
    # Major presidencies and provinces
    {"canonical": "Bengal", "type": "region", "modern": "West Bengal / Bangladesh", "variants": ["BENGAL"]},
    {"canonical": "Bombay", "type": "region", "modern": "Maharashtra / Gujarat", "variants": ["BOMBAY", "BOMBAY PRESIDENCY"]},
    {"canonical": "Madras", "type": "region", "modern": "Tamil Nadu", "variants": ["MADRAS", "MADRAS PRESIDENCY"]},
    {"canonical": "Punjab", "type": "region", "modern": "Punjab (India/Pakistan)", "variants": ["PUNJAB", "THE PUNJAB"]},
    {"canonical": "Burma", "type": "region", "modern": "Myanmar", "variants": ["BURMA", "BRITISH BURMA"]},
    {"canonical": "Assam", "type": "region", "modern": "Assam", "variants": ["ASSAM"]},
    {"canonical": "Central Provinces", "type": "region", "modern": "Madhya Pradesh", "variants": ["CENTRAL PROVINCES", "C. PROVS.", "CEN. PROVS.", "C.P."]},
    {"canonical": "North-Western Provinces", "type": "region", "modern": "Uttar Pradesh", "variants": [
        "NORTH WEST PROVINCES", "NORTH-WEST PROVINCES", "NORTH-WESTERN PROVINCES",
        "NORTH WESTERN PROVINCES", "N.W. PROVINCES", "N.W. PROVS.", "N.W.P.",
    ]},
    {"canonical": "Oudh", "type": "region", "modern": "Uttar Pradesh (Awadh)", "variants": ["OUDH", "OUDE"]},
    {"canonical": "North-Western Provinces and Oudh", "type": "region", "modern": "Uttar Pradesh", "variants": [
        "NORTH-WESTERN PROVINCES AND OUDH", "N.W.P. AND OUDH",
    ]},
    {"canonical": "United Provinces", "type": "region", "modern": "Uttar Pradesh", "variants": [
        "UNITED PROVINCES OF AGRA AND OUDH", "UNITED PROVINCES",
    ]},
    {"canonical": "Coorg", "type": "region", "modern": "Kodagu (Karnataka)", "variants": ["COORG"]},
    {"canonical": "Sind", "type": "region", "modern": "Sindh (Pakistan)", "variants": ["SIND", "SIND DISTRICT", "SCINDE"]},
    {"canonical": "Bihar and Orissa", "type": "region", "modern": "Bihar / Odisha", "variants": ["BIHAR AND ORISSA"]},
    {"canonical": "Delhi", "type": "region", "modern": "Delhi", "variants": ["DELHI"]},
    {"canonical": "Ajmer-Merwara", "type": "region", "modern": "Ajmer (Rajasthan)", "variants": ["AJMER-MERWARA", "AJMERE"]},
    {"canonical": "British Baluchistan", "type": "region", "modern": "Balochistan (Pakistan)", "variants": ["BRITISH BALUCHISTAN", "BALUCHISTAN"]},
    {"canonical": "Andaman and Nicobar Islands", "type": "region", "modern": "Andaman and Nicobar Islands", "variants": ["ANDAMAN AND NICOBAR ISLANDS"]},
    {"canonical": "North-West Frontier Province", "type": "region", "modern": "Khyber Pakhtunkhwa (Pakistan)", "variants": [
        "NORTH-WEST FRONTIER PROVINCE", "N.W.F.P.", "NWFP",
    ]},

    # Political agencies and residencies
    {"canonical": "Rajputana Agency", "type": "agency", "modern": "Rajasthan", "variants": ["RAJPUTANA AGENCY", "RAJPUTANA"]},
    {"canonical": "Central India Agency", "type": "agency", "modern": "Madhya Pradesh", "variants": ["CENTRAL INDIA AGENCY", "CENTRAL INDIA", "C. INDIA"]},
    {"canonical": "Hyderabad Residency", "type": "agency", "modern": "Telangana", "variants": ["HYDERABAD", "HYDERABAD RESIDENCY"]},
    {"canonical": "Mysore Residency", "type": "agency", "modern": "Karnataka", "variants": ["MYSORE RESIDENCY", "MYSORE"]},
    {"canonical": "Kashmir Residency", "type": "agency", "modern": "Jammu & Kashmir", "variants": ["KASHMIR RESIDENCY", "KASHMIR"]},
    {"canonical": "Baroda Residency", "type": "agency", "modern": "Vadodara (Gujarat)", "variants": ["BARODA"]},
    {"canonical": "Aden", "type": "agency", "modern": "Aden (Yemen)", "variants": ["ADEN"]},
    {"canonical": "Persian Gulf Residency", "type": "agency", "modern": "Persian Gulf states", "variants": ["PERSIAN GULF RESIDENCY"]},

    # Major cities
    {"canonical": "Calcutta", "type": "city", "parent": "Bengal", "modern": "Kolkata", "variants": ["CALCUTTA"]},
    {"canonical": "Bombay", "type": "city", "parent": "Bombay", "modern": "Mumbai", "variants": []},
    {"canonical": "Madras", "type": "city", "parent": "Madras", "modern": "Chennai", "variants": []},
    {"canonical": "Simla", "type": "city", "parent": None, "modern": "Shimla", "variants": ["SIMLA", "SHIMLA"]},
    {"canonical": "Allahabad", "type": "city", "parent": "North-Western Provinces", "modern": "Prayagraj", "variants": ["ALLAHABAD"]},
    {"canonical": "Lucknow", "type": "city", "parent": "Oudh", "modern": "Lucknow", "variants": ["LUCKNOW"]},
    {"canonical": "Lahore", "type": "city", "parent": "Punjab", "modern": "Lahore (Pakistan)", "variants": ["LAHORE"]},
    {"canonical": "Rangoon", "type": "city", "parent": "Burma", "modern": "Yangon", "variants": ["RANGOON"]},
    {"canonical": "Cawnpore", "type": "city", "parent": "North-Western Provinces", "modern": "Kanpur", "variants": ["CAWNPORE", "CAWNPOOR"]},
    {"canonical": "Patna", "type": "city", "parent": "Bengal", "modern": "Patna", "variants": ["PATNA"]},
    {"canonical": "Benares", "type": "city", "parent": "North-Western Provinces", "modern": "Varanasi", "variants": ["BENARES", "BENARAS"]},
    {"canonical": "Bareilly", "type": "city", "parent": "North-Western Provinces", "modern": "Bareilly", "variants": ["BAREILLY", "BAREILY"]},
    {"canonical": "Poona", "type": "city", "parent": "Bombay", "modern": "Pune", "variants": ["POONA"]},
    {"canonical": "Nagpur", "type": "city", "parent": "Central Provinces", "modern": "Nagpur", "variants": ["NAGPUR", "NAGPORE"]},
    {"canonical": "Roorkee", "type": "city", "parent": "North-Western Provinces", "modern": "Roorkee", "variants": ["ROORKEE", "RURKI"]},

    # London-based
    {"canonical": "London", "type": "city", "parent": None, "modern": "London", "variants": ["LONDON"]},
    {"canonical": "India Office", "type": "institution", "parent": "London", "modern": None, "variants": ["INDIA OFFICE"]},
]


class Gazetteer:
    """Location gazetteer with variant-to-canonical lookup."""

    def __init__(self) -> None:
        self.entries: Dict[str, GazetteerEntry] = {}
        self._variant_index: Dict[str, str] = {}  # normalized variant -> canonical
        self._bootstrap()

    def _bootstrap(self) -> None:
        for item in _BOOTSTRAP_REGIONS:
            entry = GazetteerEntry(
                canonical=item["canonical"],
                location_type=item["type"],
                parent_region=item.get("parent"),
                modern_name=item.get("modern"),
                variants=item.get("variants", []),
            )
            self.add_entry(entry)

    def add_entry(self, entry: GazetteerEntry) -> None:
        self.entries[entry.canonical] = entry
        self._variant_index[self._normalize(entry.canonical)] = entry.canonical
        for v in entry.variants:
            self._variant_index[self._normalize(v)] = entry.canonical

    def lookup(self, text: str) -> Optional[GazetteerEntry]:
        """Look up a location string, returning the canonical entry or None."""
        key = self._normalize(text)
        canonical = self._variant_index.get(key)
        if canonical:
            return self.entries.get(canonical)
        return None

    def resolve(self, text: str) -> Optional[str]:
        """Return canonical name for a location string, or None."""
        entry = self.lookup(text)
        return entry.canonical if entry else None

    def add_variant(self, variant: str, canonical: str) -> None:
        """Register a new variant spelling for an existing canonical entry."""
        if canonical in self.entries:
            self.entries[canonical].variants.append(variant)
            self._variant_index[self._normalize(variant)] = canonical

    def all_canonical(self) -> List[str]:
        return sorted(self.entries.keys())

    def unresolved(self, locations: List[str]) -> List[str]:
        """Return locations that don't match any gazetteer entry."""
        return [loc for loc in locations if self.lookup(loc) is None]

    def save(self, path: Path) -> None:
        """Persist the gazetteer to JSON."""
        data = {}
        for canonical, entry in sorted(self.entries.items()):
            data[canonical] = {
                "location_type": entry.location_type,
                "parent_region": entry.parent_region,
                "modern_name": entry.modern_name,
                "variants": entry.variants,
                "wikidata_id": entry.wikidata_id,
                "geonames_id": entry.geonames_id,
            }
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def load(self, path: Path) -> None:
        """Load a previously saved gazetteer, merging with bootstrap data."""
        data = json.loads(path.read_text())
        for canonical, info in data.items():
            entry = GazetteerEntry(
                canonical=canonical,
                location_type=info.get("location_type", "unknown"),
                parent_region=info.get("parent_region"),
                modern_name=info.get("modern_name"),
                variants=info.get("variants", []),
                wikidata_id=info.get("wikidata_id"),
                geonames_id=info.get("geonames_id"),
            )
            self.add_entry(entry)

    @staticmethod
    def _normalize(text: str) -> str:
        return text.strip().upper().replace(".", "").replace("-", " ").replace("  ", " ")
