"""Extraction orchestrator — chunk → LLM → validated structured output.

This module processes chunks through an LLM backend and returns validated
ChunkExtraction objects.  The LLM backend is pluggable: supply any callable
that takes (system_prompt, user_prompt) and returns a JSON string.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable, Dict, List, Optional, Protocol

from .prompts import build_prompt, _load_abbreviations
from .schema import (
    Appointment,
    ChunkExtraction,
    Confidence,
    Honour,
    Location,
    PersonMention,
    Provenance,
)

logger = logging.getLogger(__name__)


class LLMBackend(Protocol):
    """Interface for LLM backends.

    Any callable matching this signature works:
        def call(system_prompt: str, user_prompt: str) -> str:
            ...  # returns raw JSON string
    """
    def __call__(self, system_prompt: str, user_prompt: str) -> str: ...


def _parse_json_response(raw: str) -> Dict[str, Any]:
    """Extract JSON from an LLM response, handling markdown fences."""
    text = raw.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
    return json.loads(text)


def _build_person(data: dict, provenance: Provenance) -> PersonMention:
    """Convert raw JSON dict to PersonMention dataclass."""
    honours = []
    for h in data.get("honours", []):
        honours.append(Honour(
            abbreviation=h.get("abbreviation", ""),
            expanded=h.get("expanded", ""),
            date_awarded=h.get("date_awarded"),
        ))

    appointments = []
    for a in data.get("appointments", []):
        loc = a.get("location")
        location = Location(raw_text=loc) if loc else None
        appointments.append(Appointment(
            role_raw=a.get("role_raw", ""),
            role_expanded=a.get("role_expanded", ""),
            department=a.get("department"),
            location=location,
            year_appointed=a.get("year_appointed"),
            date_start=a.get("date_start"),
            is_acting=a.get("is_acting", False),
            is_officiating=a.get("is_officiating", False),
            status=a.get("status"),
        ))

    conf_str = data.get("confidence", "high")
    try:
        confidence = Confidence(conf_str)
    except ValueError:
        confidence = Confidence.MEDIUM

    return PersonMention(
        surname=data.get("surname", ""),
        given_names=data.get("given_names"),
        title=data.get("title"),
        name_raw=data.get("name_raw", ""),
        degrees=data.get("degrees", []),
        honours=honours,
        appointments=appointments,
        locations=[a.location for a in appointments if a.location],
        provenance=provenance,
        confidence=confidence,
    )


class Extractor:
    """Orchestrates LLM-based extraction from chunks."""

    def __init__(self, llm: LLMBackend, volume: str) -> None:
        self.llm = llm
        self.volume = volume
        self._abbreviations = _load_abbreviations()

    def extract_chunk(self, chunk: dict) -> ChunkExtraction:
        """Process a single chunk through the LLM and return structured output."""
        chunk_id = chunk.get("title", "unknown")
        section_path = chunk.get("section_path", [])

        system_prompt, user_prompt = build_prompt(
            chunk, self.volume, self._abbreviations
        )

        # Call the LLM
        try:
            raw_response = self.llm(system_prompt, user_prompt)
        except Exception as e:
            logger.error("LLM call failed for chunk %s: %s", chunk_id, e)
            return ChunkExtraction(
                chunk_id=chunk_id,
                chunk_type=chunk.get("chunk_type", "unknown"),
                section_path=section_path,
                volume=self.volume,
                extraction_metadata={"error": str(e)},
            )

        # Parse the response
        try:
            parsed = _parse_json_response(raw_response)
        except json.JSONDecodeError as e:
            logger.error("JSON parse failed for chunk %s: %s", chunk_id, e)
            return ChunkExtraction(
                chunk_id=chunk_id,
                chunk_type=chunk.get("chunk_type", "unknown"),
                section_path=section_path,
                volume=self.volume,
                extraction_metadata={"error": f"JSON parse error: {e}", "raw_response": raw_response[:2000]},
            )

        # Build provenance for all persons in this chunk
        provenance = Provenance(
            volume=self.volume,
            chunk_id=chunk_id,
            section_path=section_path,
            verbatim_quote=chunk.get("text", "")[:500],
            char_start=chunk.get("start_char"),
            char_end=chunk.get("end_char"),
        )

        # Convert to dataclasses
        persons = []
        for p_data in parsed.get("persons", []):
            person = _build_person(p_data, provenance)
            persons.append(person)

        locations = [
            Location(raw_text=loc)
            for loc in parsed.get("locations", [])
        ]

        return ChunkExtraction(
            chunk_id=chunk_id,
            chunk_type=chunk.get("chunk_type", "unknown"),
            section_path=section_path,
            volume=self.volume,
            persons=persons,
            locations=locations,
            year_context=parsed.get("year_context"),
            extraction_metadata={
                "person_count": len(persons),
                "location_count": len(locations),
            },
        )

    def extract_all(
        self,
        chunks: List[dict],
        max_chunks: Optional[int] = None,
        on_progress: Optional[Callable[[int, int], None]] = None,
    ) -> List[ChunkExtraction]:
        """Process multiple chunks, returning a list of extractions.

        Args:
            chunks: list of chunk dicts from the chunker
            max_chunks: optional limit for testing
            on_progress: callback(completed, total) for progress reporting
        """
        to_process = chunks[:max_chunks] if max_chunks else chunks
        total = len(to_process)
        results = []

        for i, chunk in enumerate(to_process):
            extraction = self.extract_chunk(chunk)
            results.append(extraction)

            if on_progress:
                on_progress(i + 1, total)

        return results
