"""Chunker for India Office / India List volumes.

This module extracts structured chunks aligned with administrative headings from
India Office Lists (a.k.a. India Civil & Military Lists). The output is
optimized for downstream entity and relationship extraction pipelines targeting
colonial administrative staff.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

HeadingMatch = re.Match[str]

# Headings are typically full uppercase lines optionally wrapped in markdown
# emphasis markers. We capture the heading text without trailing whitespace so
# subsequent processing can determine hierarchy and classification.
HEADING_PATTERN = re.compile(
    r"(?m)^(?:\*\*)?(?P<heading>[A-Z][A-Z0-9\s&'\-/,.;:()]+?)(?:\*\*)?(?=\n{1,2})",
)

NAME_PATTERN = re.compile(
    r"\b[A-Z][A-Za-z'’\-]+(?:\s+[A-Z][A-Za-z'’\-]+)*,\s+(?:Sir\s+)?[A-Z][^\n,]*\."
)

PAGE_TOKEN_PATTERN = re.compile(r"\b\d{1,3}(?:[ab])?\b")

ADVERT_KEYWORDS = {
    "LIMITED",
    "PRICE",
    "PIANOS",
    "ORGAN",
    "SHIRT",
    "PATENT",
    "WAREHOUSE",
    "DISCOUNT",
    "WHOLESALE",
    "CATALOGUE",
    "CATALOGUES",
    "PATTERNS",
    "FACTORY",
}

TOP_LEVEL_SECTIONS = {
    "INDIA OFFICE",
    "CIVIL SERVICE",
    "MILITARY",
    "GENERAL",
    "EXAMINATIONS FOR THE CIVIL SERVICE OF INDIA",
    "FOREST EXAMINATION",
    "FOREST SERVICE IN INDIA",
}

CHAPTER_PREFIX = "CHAPTER "

REGION_ALIASES = {
    "ASSAM",
    "BENGAL",
    "BOMBAY",
    "BURMA",
    "CENTRAL PROVINCES",
    "COORG",
    "HYDERABAD",
    "INDIA",
    "MADRAS",
    "NORTH WEST PROVINCES",
    "NORTH-WEST PROVINCES",
    "NORTH-WESTERN PROVINCES",
    "NORTH WESTERN PROVINCES",
    "N.W. PROVINCES",
    "N.W.P.",
    "NORTH-WESTERN PROVINCES AND OUDH",
    "ORISSA",
    "PUNJAB",
    "QUETTA DISTRICT",
    "SIND DISTRICT",
    "SIND",
    "QUETTA",
    "BOMBAY PRESIDENCY",
    "UNITED PROVINCES OF AGRA AND OUDH",
    "UNITED PROVINCES",
    "NORTH-WEST FRONTIER PROVINCE",
    "N.W.F.P.",
    "NWFP",
    "BIHAR AND ORISSA",
    "DELHI",
    "AJMER-MERWARA",
    "BRITISH BALUCHISTAN",
    "ANDAMAN AND NICOBAR ISLANDS",
    "RAJPUTANA AGENCY",
    "CENTRAL INDIA AGENCY",
    "MYSORE RESIDENCY",
    "KASHMIR RESIDENCY",
    "ADEN",
    "PERSIAN GULF RESIDENCY",
}

SKIP_HEADINGS = {
    "CONTENTS",
    "TABLE OF CONTENTS",
    "INDEX",
    "ILLUSTRATIONS",
    "MAPS",
    "PREFACE",
    "ADVERTISEMENTS",
    "NOTE",
    "LIST OF TABLES",
    "RULES FOR ADMISSION",
    "FORM OF TESTIMONIAL",
}


@dataclass
class Block:
    heading: str
    start_idx: int
    content_start_idx: int
    end_idx: int
    text: str

    def clamp_text(self) -> str:
        return self.text.strip()


@dataclass
class Chunk:
    title: str
    start_char: int
    end_char: int
    pages: Tuple[Optional[int], Optional[int]]
    section_path: List[str]
    chunk_type: str
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class IndiaOfficeChunker:
    """Chunk India Office Lists into hierarchical administrative sections."""

    def __init__(
        self,
        min_chunk_length: int = 250,
        roster_name_threshold: int = 2,
    ) -> None:
        self.min_chunk_length = min_chunk_length
        self.roster_name_threshold = roster_name_threshold
        self.page_starts: List[int] = []
        self.page_numbers: List[int] = []

    # ------------------------------------------------------------------
    def process_file(self, path: Path) -> Dict[str, Any]:
        data = json.loads(Path(path).read_text())
        text = data["text"]
        attributes = data.get("attributes") or {}
        return self.chunk_text(text, attributes)

    def chunk_text(self, text: str, attributes: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if attributes:
            self._prepare_page_index(attributes)

        blocks = self._split_blocks(text)

        top_context: Optional[str] = None
        chapter_context: Optional[str] = None
        region_context: Optional[str] = None

        chunks: List[Chunk] = []
        stats = Counter()

        for block in blocks:
            raw_heading = self._clean_heading(block.heading)
            body_text = block.clamp_text()

            if self._should_skip_heading(raw_heading):
                continue

            classification = self._classify_block(raw_heading, body_text)
            chunk_type = classification["chunk_type"]

            # Update hierarchical context before potential skip so subsequent
            # sections inherit the correct parent even when the current block is
            # a table of contents entry.
            if self._is_top_level(raw_heading):
                top_context = raw_heading
                chapter_context = None
                region_context = None
            elif self._is_chapter_heading(raw_heading):
                chapter_context = raw_heading
                region_context = None
            elif self._is_region_heading(raw_heading):
                region_context = raw_heading

            if chunk_type in {"toc", "noise", "advertisement"}:
                stats[chunk_type] += 1
                continue

            section_path: List[str] = []
            if top_context:
                section_path.append(top_context)
            if chapter_context and chapter_context != raw_heading:
                section_path.append(chapter_context)
            if region_context and region_context != raw_heading:
                section_path.append(region_context)
            if not section_path or section_path[-1] != raw_heading:
                section_path.append(raw_heading)

            if len(body_text) < self.min_chunk_length and chunk_type == "narrative":
                # Skip tiny narrative fragments unless they carry signal content.
                if (
                    classification.get("name_hits", 0) == 0
                    and not classification.get("has_table", False)
                    and not any(ch.isdigit() for ch in body_text)
                    and "£" not in body_text
                ):
                    stats["skipped_short"] += 1
                    continue

            chunk = Chunk(
                title=raw_heading,
                start_char=block.content_start_idx,
                end_char=block.end_idx,
                pages=self._pages_for_range(block.content_start_idx, block.end_idx),
                section_path=section_path,
                chunk_type=chunk_type,
                text=body_text,
                metadata={
                    "char_length": len(body_text),
                    "name_hits": classification.get("name_hits", 0),
                    "has_table": classification.get("has_table", False),
                    "content_density": classification.get("content_density"),
                },
            )
            chunks.append(chunk)
            stats[chunk.chunk_type] += 1

        return {
            "chunks": [self._chunk_to_dict(chunk) for chunk in chunks],
            "statistics": dict(stats),
            "total_chunks": len(chunks),
        }

    # ------------------------------------------------------------------
    def _split_blocks(self, text: str) -> List[Block]:
        matches = list(HEADING_PATTERN.finditer(text))
        blocks: List[Block] = []
        for idx, match in enumerate(matches):
            heading = match.group("heading").strip()
            start_idx = match.start()
            content_start = match.end()
            end_idx = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            block_text = text[content_start:end_idx]
            if not block_text.strip():
                continue
            blocks.append(
                Block(
                    heading=heading,
                    start_idx=start_idx,
                    content_start_idx=content_start,
                    end_idx=end_idx,
                    text=block_text,
                )
            )
        return blocks

    def _clean_heading(self, heading: str) -> str:
        normalized = heading.strip().strip("* ")
        normalized = re.sub(r"\s+", " ", normalized)
        normalized = normalized.rstrip(".,;:-")
        return normalized.upper()

    def _should_skip_heading(self, heading: str) -> bool:
        if not heading:
            return True
        if heading in SKIP_HEADINGS:
            return True
        if heading.startswith("CHAPTER ") and heading.endswith("—CONTINUED"):
            return False
        if heading.endswith("—CONTINUED"):
            return False
        if heading.startswith("SCHEDULE"):
            return False
        if heading in {"NOTE", "NOTES"}:
            return True
        return False

    def _classify_block(self, heading: str, body: str) -> Dict[str, Any]:
        text = body.strip()
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        has_table = any(line.startswith("|") for line in lines)
        name_hits = len(NAME_PATTERN.findall(body))
        uppercase_lines = sum(1 for line in lines if line.isupper())
        upper_heading = heading.upper()
        upper_body = body.upper()
        advert_markers = sum(
            1 for kw in ADVERT_KEYWORDS if re.search(rf"\b{re.escape(kw)}\b", upper_heading)
        ) + sum(
            1 for kw in ADVERT_KEYWORDS if re.search(rf"\b{re.escape(kw)}\b", upper_body)
        )
        contains_currency = "£" in body or re.search(r"\bRs?\.\s*\d", body)

        # Determine density of text lines with actual sentences.
        sentence_like = sum(1 for line in lines if re.search(r"[a-z]{3,}", line))
        content_density = sentence_like / max(len(lines), 1)

        toc_lines = sum(1 for line in lines if self._is_toc_entry(line))
        if toc_lines >= max(3, int(len(lines) * 0.6)):
            return {"chunk_type": "toc"}

        if (advert_markers >= 3 and content_density < 0.5) or (
            advert_markers >= 1
            and contains_currency
            and content_density < 0.3
            and name_hits == 0
        ):
            return {
                "chunk_type": "advertisement",
                "advert_markers": advert_markers,
                "contains_currency": bool(contains_currency),
                "content_density": content_density,
                "name_hits": name_hits,
            }

        if has_table or name_hits >= self.roster_name_threshold:
            return {
                "chunk_type": "roster",
                "name_hits": name_hits,
                "has_table": has_table,
                "content_density": content_density,
            }

        if len(text) < 120 and uppercase_lines / max(len(lines), 1) > 0.5:
            return {"chunk_type": "noise"}

        return {
            "chunk_type": "narrative",
            "name_hits": name_hits,
            "has_table": has_table,
            "content_density": content_density,
        }

    def _is_toc_entry(self, line: str) -> bool:
        if not line:
            return False
        if PAGE_TOKEN_PATTERN.search(line):
            if ":" in line or ";" in line:
                return True
            if re.search(r"\b\d{1,3}(?:[ab])?(?:\.|;)?$", line):
                return True
        if line.endswith("...."):
            return True
        return False

    def _is_top_level(self, heading: str) -> bool:
        return heading in TOP_LEVEL_SECTIONS

    def _is_chapter_heading(self, heading: str) -> bool:
        return heading.startswith(CHAPTER_PREFIX)

    def _is_region_heading(self, heading: str) -> bool:
        if heading in REGION_ALIASES:
            return True
        for alias in REGION_ALIASES:
            if heading.startswith(alias + " "):
                return True
        return False

    def _prepare_page_index(self, attributes: Dict[str, Any]) -> None:
        page_ranges = attributes.get("pdf_page_numbers") or []
        self.page_starts = [start for (start, _end, _page) in page_ranges]
        self.page_numbers = [page for (_start, _end, page) in page_ranges]

    def _pages_for_range(self, start: int, end: int) -> Tuple[Optional[int], Optional[int]]:
        if not self.page_starts:
            return (None, None)
        start_page = self._page_for_index(start)
        end_page = self._page_for_index(end)
        return (start_page, end_page)

    def _page_for_index(self, idx: int) -> Optional[int]:
        if not self.page_numbers:
            return None

        current_page = self.page_numbers[0]
        for start, page in zip(self.page_starts, self.page_numbers):
            if idx < start:
                break
            current_page = page
        return current_page

    def _chunk_to_dict(self, chunk: Chunk) -> Dict[str, Any]:
        return {
            "title": chunk.title,
            "section_path": chunk.section_path,
            "chunk_type": chunk.chunk_type,
            "start_char": chunk.start_char,
            "end_char": chunk.end_char,
            "pages": chunk.pages,
            "text": chunk.text,
            "metadata": chunk.metadata,
        }


__all__ = ["IndiaOfficeChunker"]
