"""Data models for knowledge graph extraction.

These models define the structured output expected from LLM extraction.
They are intentionally flat and permissive — the LLM should populate what
it can confidently extract from a chunk and leave the rest as None.
Disambiguation and cross-referencing happen downstream.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Confidence(str, Enum):
    """How confident the extraction is."""
    HIGH = "high"        # unambiguous, clearly stated
    MEDIUM = "medium"    # reasonable inference from context
    LOW = "low"          # plausible but uncertain


@dataclass
class Provenance:
    """Traces every extracted fact back to the source text."""
    volume: str                     # e.g. "iliol_1896"
    chunk_id: str                   # chunk identifier from the chunker
    section_path: List[str]         # e.g. ["BENGAL", "SECRETARIAT"]
    verbatim_quote: str             # exact text the fact was extracted from
    char_start: Optional[int] = None
    char_end: Optional[int] = None


@dataclass
class Location:
    """A location mention, to be canonicalized into the gazetteer."""
    raw_text: str                   # as it appears in the source
    canonical: Optional[str] = None # resolved canonical name
    location_type: Optional[str] = None  # "region", "city", "district", "institution"
    parent_region: Optional[str] = None  # e.g. "Bengal" for "Calcutta"
    confidence: Confidence = Confidence.HIGH


@dataclass
class Appointment:
    """A role or position held by a person."""
    role_raw: str                   # as it appears: "Jt. Mag. and Dy. Coll."
    role_expanded: str              # expanded: "Joint Magistrate and Deputy Collector"
    department: Optional[str] = None
    location: Optional[Location] = None
    year_appointed: Optional[str] = None   # year from context (e.g. section heading "1882")
    date_start: Optional[str] = None       # if a specific date is given
    date_end: Optional[str] = None
    is_acting: bool = False
    is_officiating: bool = False
    status: Optional[str] = None           # "on furlough", "retired", etc.
    confidence: Confidence = Confidence.HIGH


@dataclass
class Honour:
    """A decoration, order, or title."""
    abbreviation: str               # "C.S.I."
    expanded: str                   # "Companion of the Order of the Star of India"
    date_awarded: Optional[str] = None
    confidence: Confidence = Confidence.HIGH


@dataclass
class PersonMention:
    """A single mention of a person in a chunk.

    This is NOT a canonical person record — it represents one mention
    in one chunk. Disambiguation merges these into canonical records later.
    """
    # Name fields
    surname: str
    given_names: Optional[str] = None
    title: Optional[str] = None          # "Sir", "Raja", "Nawab", etc.
    name_raw: str = ""                   # full name as it appears in source

    # Qualifications
    degrees: List[str] = field(default_factory=list)      # ["B.A.", "M.A."]
    honours: List[Honour] = field(default_factory=list)

    # Career
    appointments: List[Appointment] = field(default_factory=list)

    # All locations mentioned in connection with this person
    locations: List[Location] = field(default_factory=list)

    # Provenance
    provenance: Optional[Provenance] = None
    confidence: Confidence = Confidence.HIGH

    # For disambiguation — populated downstream, not by the LLM
    canonical_id: Optional[str] = None


@dataclass
class ChunkExtraction:
    """The complete extraction result from a single chunk."""
    chunk_id: str
    chunk_type: str                 # "roster", "narrative", etc.
    section_path: List[str]
    volume: str
    persons: List[PersonMention] = field(default_factory=list)
    locations: List[Location] = field(default_factory=list)  # chunk-level locations
    year_context: Optional[str] = None   # if the chunk has a year heading
    extraction_metadata: Dict[str, Any] = field(default_factory=dict)
