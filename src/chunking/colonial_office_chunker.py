"""Robust chunker for Colonial Office Lists.

Parses semi-structured colonial yearbooks into territory-aligned chunks with
section metadata for downstream GraphRAG/knowledge-graph use.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from bisect import bisect_right
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

# Heading pattern captures uppercase headings while keeping the trailing
# blank lines outside the match so adjacent headings are not skipped.
HEADING_PATTERN = re.compile(
    r"(?m)^(?:\*\*)?([A-Z][A-Z\s\-\'&,]+)\.(?:\*\*)?(?=\n{1,2})",
)

TITLE_HEADING_PATTERN = re.compile(
    r"(?m)^(?:\*\*)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\.(?:\*\*)?(?=\n{1,2})"
)

TITLE_CASE_TERRITORY_WHITELIST = {
    "ANTIGUA",
    "BAHAMAS",
    "BARBADOS",
    "BASUTOLAND",
    "BERMUDA",
    "BRITISH CENTRAL AFRICA",
    "BRITISH EAST AFRICA",
    "BRITISH GUIANA",
    "BRITISH HONDURAS",
    "BRITISH NEW GUINEA",
    "BRUNEI",  # safeguard for later editions
    "CEYLON",
    "CYPRUS",
    "DOMINICA",
    "FALKLAND ISLANDS",
    "FIJI",
    "GAMBIA",
    "GIBRALTAR",
    "GOLD COAST",
    "GOLD COAST COLONY",
    "GRENADA",
    "HONG KONG",
    "JAMAICA",
    "LAGOS",
    "LEEWARD ISLANDS",
    "MALTA",
    "MAURITIUS",
    "MONTSERRAT",
    "NATAL",
    "NIGER COAST PROTECTORATE",
    "NEW SOUTH WALES",
    "NEW ZEALAND",
    "NORTH BORNEO",
    "QUEENSLAND",
    "SEYCHELLES ISLANDS",
    "SIERRA LEONE",
    "SOUTH AUSTRALIA",
    "ST. HELENA",
    "ST. LUCIA",
    "ST. VINCENT",
    "TASMANIA",
    "TOBAGO",
    "TRINIDAD",
    "TURKS ISLANDS",
    "UGANDA PROTECTORATE",
    "VICTORIA",
    "WESTERN AUSTRALIA",
    "WESTERN PACIFIC",
    "ZULULAND",
}

SECTION_CANDIDATE_PATTERN = re.compile(r"(?m)^(?P<header>[A-Z][^|]{2,80}\.)$")

LOWER_STOPWORDS = {
    "and",
    "of",
    "the",
    "for",
    "in",
    "to",
    "with",
    "a",
    "an",
    "on",
    "by",
    "from",
    "or",
}

KEYWORD_GROUPS = {
    "geography": [
        "situation and area",
        "situation, area",
        "situation.",
        "area.",
        "peninsula",
        "island",
        "coast",
        "bounded",
        "latitude",
        "longitude",
        "square miles",
    ],
    "population": ["population", "census", "inhabitants"],
    "government": [
        "government",
        "governor",
        "administrator",
        "commissioner",
        "legislative council",
        "executive council",
        "assembly",
        "privy council",
        "crown colony",
    ],
    "judicial": ["judicial", "judge", "magistrate", "court"],
    "finance": [
        "finance",
        "finances",
        "revenue",
        "expenditure",
        "public debt",
        "customs",
        "tax",
    ],
    "trade": ["trade", "imports", "exports", "commerce"],
    "infrastructure": [
        "railway",
        "telegraph",
        "postal",
        "harbour",
        "harbor",
        "public works",
        "canal",
    ],
    "security": ["military", "naval", "police", "defence", "defense"],
    "education": ["education", "school", "college", "university"],
    "religion": ["church", "bishop", "diocese", "mission"],
}

ADMIN_KEYWORDS = {
    "DEPARTMENT",
    "TREASURY",
    "AUDIT",
    "COUNCIL",
    "COURT",
    "OFFICE",
    "OFFICES",
    "OFFICIALS",
    "SENATE",
    "ASSEMBLY",
    "HOUSE OF",
    "MINISTER",
    "SECRETARY",
    "CLERGY",
    "DIOCESE",
    "BISHOPS",
}

SKIP_KEYWORDS = {
    "CONTENTS",
    "INDEX",
    "TABLE OF",
    "LIST OF",
    "ESTABLISHMENTS IN THE COLONIES",
    "ESTABLISHMENT",
    "RULES",
    "REGULATIONS",
    "ORDERS",
    "PREFACE",
    "INTRODUCTION",
    "ADVERTISE",
    "ADVERTIS",
    "CATALOGUE",
    "PRICE",
    "BANK",
    "COMPANY",
    "LIMITED",
    "RAILWAY TIMETABLE",
    "CROWN AGENTS",
    "EXPORTS",
    "IMPORTS",
    "FINANCES",
    "FINANCIAL",
    "TRADE",
}

DOMINION_ALIASES: Dict[str, Dict[str, Any]] = {
    "DOMINION OF CANADA": {
        "aliases": {"DOMINION OF CANADA"},
        "subunits": {
            "THE DOMINION": {"kind": "federal"},
            "ONTARIO": {"kind": "province"},
            "QUEBEC": {"kind": "province"},
            "NOVA SCOTIA": {"kind": "province"},
            "NEW BRUNSWICK": {"kind": "province"},
            "MANITOBA AND KEEWATIN": {"kind": "province"},
            "MANITOBA": {"kind": "province"},
            "THE NORTH WEST TERRITORIES": {"kind": "territory"},
            "NORTH WEST TERRITORY": {"kind": "territory"},
            "PRINCE EDWARD ISLAND": {"kind": "province"},
            "BRITISH COLUMBIA": {"kind": "province"},
            "SEAT OF GOVERNMENT, QUEBEC": {"kind": "admin"},
            "THE QUEEN'S PRIVY COUNCIL FOR CANADA": {"kind": "admin"},
            "TREASURY BOARD": {"kind": "admin"},
            "THE SUPREME COURT OF CANADA": {"kind": "admin"},
            "THE COURT OF EXCHEQUER OF CANADA": {"kind": "admin"},
            "THE SENATE OF CANADA": {"kind": "admin"},
        },
    },
    "THE LEEWARD ISLANDS": {
        "aliases": {"THE LEEWARD ISLANDS", "LEEWARD ISLANDS"},
        "subunits": {
            "ANTIGUA": {"kind": "presidency"},
            "DOMINICA": {"kind": "presidency"},
            "ST. CHRISTOPHER": {"kind": "presidency"},
            "ST. CHRISTOPHER AND NEVIS": {"kind": "presidency"},
            "NEVIS": {"kind": "presidency"},
            "MONTSERRAT": {"kind": "presidency"},
            "VIRGIN ISLANDS": {"kind": "presidency"},
            "THE VIRGIN ISLANDS": {"kind": "presidency"},
        },
    },
}

SECTION_NORMALIZER: Dict[str, str] = {
    "situation and area": "geography",
    "description and climate": "geography",
    "climate": "geography",
    "population and industry": "economy",
    "population": "demographics",
    "industry": "economy",
    "history": "history",
    "currency and banking": "finance",
    "currency": "finance",
    "banking": "finance",
    "education": "education",
    "means of communication": "infrastructure",
    "internal communications": "infrastructure",
    "communications": "infrastructure",
    "government and constitution": "government",
    "government": "government",
    "local government": "government",
    "executive council": "government",
    "legislative council": "government",
    "judicial": "judicial",
    "supreme court": "judicial",
    "exports": "trade",
    "imports": "trade",
    "trade": "trade",
    "revenue": "finance",
    "finances": "finance",
    "public debt": "finance",
    "military": "security",
    "naval": "security",
    "police": "security",
}


@dataclass
class Block:
    heading: str
    start_idx: int
    content_start_idx: int
    end_idx: int
    text: str
    prefix_headings: List[str] = field(default_factory=list)
    score: float = 0.0
    keyword_hits: List[str] = field(default_factory=list)
    uppercase_ratio: float = 0.0
    length: int = 0
    classification: str = ""
    reasons: List[str] = field(default_factory=list)

    @property
    def normalized_heading(self) -> str:
        return self.heading.strip().upper()


def _sha1(text: str) -> str:
    normalized = re.sub(r"\s+", "", text.lower())
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()


class ColonialOfficeChunker:
    """Parse Colonial Office Lists into colony-aligned chunks.

    The extractor produces a primary record for each territorial narrative and
    tags any later occurrences of the same heading (usually statistical
    appendices or staff directories) as supplements so downstream consumers can
    decide how to join them back together."""
    def __init__(
        self,
        high_score_threshold: float = 6.0,
        review_lower: float = 4.25,
        min_length: int = 1500,
        hierarchy: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> None:
        self.high_score_threshold = high_score_threshold
        self.review_lower = review_lower
        self.min_length = min_length
        self.hierarchy = hierarchy or DOMINION_ALIASES
        self.page_starts: List[int] = []
        self.page_numbers: List[int] = []
        self.subunit_names = {
            name
            for data in self.hierarchy.values()
            for name in data.get("subunits", {})
        }

    # Public API -----------------------------------------------------------------
    def process_file(self, path: Path) -> Dict[str, Any]:
        data = json.loads(Path(path).read_text())
        text = data["text"]
        attributes = data.get("attributes") or {}
        return self.chunk_text(text, attributes)

    def chunk_text(self, text: str, attributes: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if attributes:
            self._prepare_page_index(attributes)
        blocks = self._split_blocks(text)
        analysed_blocks = [self._analyze_block(block) for block in blocks]

        territories: List[Dict[str, Any]] = []
        duplicates: List[Dict[str, Any]] = []
        review_items: List[Dict[str, Any]] = []

        seen_fingerprints: Dict[str, Dict[str, Any]] = {}
        current_territory: Optional[Dict[str, Any]] = None
        active_container: Optional[Dict[str, Any]] = None

        def finalize_active() -> None:
            nonlocal current_territory, active_container
            if not current_territory:
                return
            self._attach_sections(current_territory)

            if (
                territories
                and territories[-1]["name"] == current_territory["name"]
                and territories[-1]["kind"] == current_territory["kind"]
            ):
                previous = territories[-1]
                previous_text = previous["text"].strip()
                combined_text = previous_text + "\n\n" + current_territory["text"].strip()
                previous["text"] = combined_text
                previous["end_char"] = current_territory["end_char"]
                previous["pages"] = (
                    previous["pages"][0],
                    current_territory["pages"][1],
                )
                previous["metadata"]["length"] = len(combined_text)
                previous["metadata"]["reasons"] = list(
                    set(previous["metadata"].get("reasons", []))
                    | set(current_territory["metadata"].get("reasons", []))
                )
                previous["keyword_hits"] = list(
                    sorted(
                        set(previous.get("keyword_hits", []))
                        | set(current_territory.get("keyword_hits", []))
                    )
                )
                self._attach_sections(previous)
                current_territory = None
                active_container = None
                return

            fingerprint = _sha1(current_territory["text"])
            current_territory["fingerprint"] = fingerprint
            key = f"{current_territory['name']}::{fingerprint}"
            if key in seen_fingerprints:
                current_territory["is_duplicate"] = True
                current_territory["duplicate_of"] = seen_fingerprints[key]["fingerprint"]
                duplicates.append(
                    {
                        "name": current_territory["name"],
                        "fingerprint": fingerprint,
                        "original_index": seen_fingerprints[key]["index"],
                        "duplicate_index": len(territories),
                    }
                )
            else:
                current_territory["is_duplicate"] = False
                current_territory["duplicate_of"] = None
                seen_fingerprints[key] = {
                    "fingerprint": fingerprint,
                    "index": len(territories),
                }
            territories.append(current_territory)
            current_territory = None
            active_container = None

        for block in analysed_blocks:
            cls = block.classification
            if cls == "skip":
                continue

            if cls == "dominion":
                finalize_active()
                territory = self._build_territory(block, kind="dominion")
                current_territory = territory
                active_container = territory
                continue

            if cls == "colony_high" or cls == "colony_candidate":
                finalize_active()
                territory = self._build_territory(block, kind="colony")
                territory["needs_review"] = cls == "colony_candidate"
                if territory["needs_review"]:
                    review_items.append(
                        {
                            "name": territory["name"],
                            "score": block.score,
                            "start_idx": block.start_idx,
                            "end_idx": block.end_idx,
                            "reason": "score in review range",
                        }
                    )
                current_territory = territory
                continue

            if cls == "province":
                if active_container:
                    subunit = self._build_territory(block, kind="subunit")
                    subunit["needs_review"] = False
                    active_container.setdefault("subunits", []).append(subunit)
                else:
                    finalize_active()
                    territory = self._build_territory(block, kind="colony")
                    current_territory = territory
                continue

            if cls == "admin":
                target = active_container if active_container else current_territory
                if target:
                    target.setdefault("admin_sections", []).append(
                        {
                            "title": self._format_heading(block),
                            "start_char": block.start_idx,
                            "end_char": block.end_idx,
                            "pages": self._pages_for_range(block.start_idx, block.end_idx),
                            "text": block.text.strip(),
                        }
                    )
                continue

            if cls == "other" and current_territory:
                current_territory.setdefault("attachments", []).append(
                    {
                        "title": self._format_heading(block),
                        "start_char": block.start_idx,
                        "end_char": block.end_idx,
                        "pages": self._pages_for_range(block.start_idx, block.end_idx),
                        "text": block.text.strip(),
                        "notes": block.reasons,
                    }
                )

        finalize_active()

        grouped_by_name: Dict[str, List[int]] = {}
        for idx, territory in enumerate(territories):
            grouped_by_name.setdefault(territory["name"], []).append(idx)

        # Convert repeated headings into primary/supplement pairs so we retain
        # later material (appendices, staff directories, etc.) without merging it
        # blindly into the first chunk.
        for name, indices in grouped_by_name.items():
            primary_idx = indices[0]
            primary = territories[primary_idx]
            primary.setdefault("role", "primary")
            for supplement_number, idx in enumerate(indices[1:], start=2):
                territory = territories[idx]
                territory["role"] = "appendix"
                territory["supplement_for"] = primary.get("fingerprint")
                territory.setdefault("flags", []).append("supplementary-entry")
                territory["metadata"].setdefault("notes", []).append("tagged_as_appendix")
                primary.setdefault("supplements", []).append(
                    {
                        "index": idx,
                        "pages": territory["pages"],
                        "fingerprint": territory.get("fingerprint"),
                    }
                )
                review_items.append(
                    {
                        "name": territory["name"],
                        "score": territory["score"],
                        "start_idx": territory["start_char"],
                        "end_idx": territory["end_char"],
                        "reason": f"supplementary entry {supplement_number} for {name}",
                    }
                )

        statistics = {
            "total_blocks": len(analysed_blocks),
            "territories": len(territories),
            "duplicates": len(duplicates),
            "review_items": len(review_items),
        }

        return {
            "territories": territories,
            "duplicates": duplicates,
            "review_queue": review_items,
            "statistics": statistics,
        }

    # Internal helpers -----------------------------------------------------------
    def _split_blocks(self, text: str) -> List[Block]:
        raw_blocks: List[Block] = []
        matches = list(HEADING_PATTERN.finditer(text))

        seen_positions = {match.start(1) for match in matches}
        title_matches: List[Tuple[int, re.Match[str]]] = []
        for match in TITLE_HEADING_PATTERN.finditer(text):
            start = match.start(1)
            if start in seen_positions:
                continue
            name = match.group(1).strip()
            upper_name = name.upper()
            if upper_name not in TITLE_CASE_TERRITORY_WHITELIST:
                continue
            title_matches.append((start, match))

        matches.extend(m for _, m in sorted(title_matches, key=lambda item: item[0]))
        matches.sort(key=lambda m: m.start(1))
        if not matches:
            return []
        for idx, match in enumerate(matches):
            heading = match.group(1).strip()
            start = match.start(1)
            # skip the trailing period and newline(s)
            after_heading = match.end()
            if text[after_heading:after_heading + 2] == "\n\n":
                content_start = after_heading + 2
            else:
                content_start = after_heading + 1
            next_start = matches[idx + 1].start(1) if idx + 1 < len(matches) else len(text)
            block_text = text[content_start:next_start]
            raw_blocks.append(
                Block(
                    heading=heading,
                    start_idx=start,
                    content_start_idx=content_start,
                    end_idx=next_start,
                    text=block_text,
                )
            )

        merged_blocks: List[Block] = []
        pending_prefix: List[str] = []
        for block in raw_blocks:
            trimmed = block.text.strip()
            if not trimmed:
                pending_prefix.append(block.heading)
                continue
            if len(trimmed) < 160 and self._looks_like_prefix(block.heading):
                pending_prefix.append(block.heading)
                continue
            if pending_prefix:
                block.prefix_headings.extend(pending_prefix)
                pending_prefix = []
            merged_blocks.append(block)
        return merged_blocks

    def _analyze_block(self, block: Block) -> Block:
        text_sample = block.text[:3500].lower()
        hits: List[str] = []
        score = 0.0
        for label, keywords in KEYWORD_GROUPS.items():
            if any(keyword in text_sample for keyword in keywords):
                hits.append(label)
                score += 1.0
        if "colony" in text_sample or "protectorate" in text_sample:
            score += 0.5
        trimmed = block.text.strip()
        block.length = len(trimmed)
        if block.length > 4000:
            score += 1.0
        if block.length > 10000:
            score += 1.0
        snippet = trimmed[:2000]
        letters = sum(1 for ch in snippet if ch.isalpha()) or 1
        uppercase_letters = sum(1 for ch in snippet if ch.isupper())
        block.uppercase_ratio = uppercase_letters / letters
        if block.uppercase_ratio > 0.3:
            score -= (block.uppercase_ratio - 0.3) * 4
        block.score = score
        block.keyword_hits = hits
        block.classification = self._classify_block(block)
        return block

    def _classify_block(self, block: Block) -> str:
        heading = block.normalized_heading
        if any(keyword in heading for keyword in SKIP_KEYWORDS):
            block.reasons.append("skip_keyword")
            return "skip"

        if block.prefix_headings:
            for prefix in block.prefix_headings:
                if self._is_container_prefix(prefix):
                    block.reasons.append("dominion_prefix")
                    return "dominion"

        if self._is_container_prefix(block.heading):
            block.reasons.append("dominion_heading")
            return "dominion"

        if any(keyword in heading for keyword in ADMIN_KEYWORDS):
            block.reasons.append("admin_keyword")
            return "admin"

        if heading in self.subunit_names:
            block.reasons.append("known_subunit")
            return "province"

        if block.length < 400 and block.score < 2:
            block.reasons.append("too_short")
            return "skip"

        if block.length < self.min_length and block.score < self.review_lower:
            block.reasons.append("weak_content")
            return "other"

        if block.score >= self.high_score_threshold and block.length >= self.min_length:
            return "colony_high"

        if block.score >= self.review_lower and block.length >= self.min_length:
            return "colony_candidate"

        block.reasons.append("low_score")
        return "other"

    def _build_territory(self, block: Block, kind: str) -> Dict[str, Any]:
        heading_variants = block.prefix_headings + [block.heading]
        canonical_name = self._select_canonical_name(heading_variants)
        territory = {
            "name": canonical_name,
            "heading_variants": heading_variants,
            "kind": kind,
            "score": block.score,
            "confidence": self._score_to_confidence(block.score),
            "keyword_hits": block.keyword_hits,
            "start_char": block.start_idx,
            "end_char": block.end_idx,
            "pages": self._pages_for_range(block.start_idx, block.end_idx),
            "text": block.text.strip(),
            "needs_review": False,
            "metadata": {
                "uppercase_ratio": round(block.uppercase_ratio, 3),
                "length": block.length,
                "reasons": block.reasons,
            },
        }
        return territory

    def _attach_sections(self, territory: Dict[str, Any]) -> None:
        sections = self._detect_sections(territory["text"])
        territory["sections"] = sections

    def _score_to_confidence(self, score: float) -> float:
        clamped = max(0.0, min(10.0, score))
        return round(0.1 + 0.08 * clamped, 3)

    def _detect_sections(self, text: str) -> List[Dict[str, Any]]:
        matches = list(SECTION_CANDIDATE_PATTERN.finditer(text))
        headers: List[Tuple[int, str]] = []
        for match in matches:
            header = match.group("header").strip()
            if self._valid_section_header(header):
                headers.append((match.start(), header))
        if not headers:
            return [
                {
                    "title": "Introduction",
                    "category": "overview",
                    "text": text.strip(),
                }
            ]
        sections: List[Dict[str, Any]] = []
        for idx, (pos, header) in enumerate(headers):
            start = pos + len(header) + 1
            end = headers[idx + 1][0] if idx + 1 < len(headers) else len(text)
            body = text[start:end].strip()
            if not body:
                continue
            normalized = self._normalize_section_title(header)
            category = SECTION_NORMALIZER.get(normalized, "other")
            sections.append(
                {
                    "title": header,
                    "category": category,
                    "text": body,
                }
            )
        intro_start = 0
        first_header_pos = headers[0][0]
        intro_text = text[intro_start:first_header_pos].strip()
        if intro_text:
            sections.insert(
                0,
                {
                    "title": "Introduction",
                    "category": "overview",
                    "text": intro_text,
                },
            )
        return sections

    def _prepare_page_index(self, attributes: Dict[str, Any]) -> None:
        ranges = attributes.get("pdf_page_numbers") or []
        self.page_starts = [rng[0] for rng in ranges]
        self.page_numbers = [rng[2] for rng in ranges]

    def _pages_for_range(self, start: int, end: int) -> Tuple[Optional[int], Optional[int]]:
        if not self.page_starts:
            return (None, None)
        start_page = self._page_for_position(start)
        end_page = self._page_for_position(end)
        return (start_page, end_page)

    def _page_for_position(self, pos: int) -> Optional[int]:
        if not self.page_starts:
            return None
        idx = bisect_right(self.page_starts, pos) - 1
        if idx < 0:
            return self.page_numbers[0]
        if idx >= len(self.page_numbers):
            return self.page_numbers[-1]
        return self.page_numbers[idx]

    # Utility predicates --------------------------------------------------------
    def _looks_like_prefix(self, heading: str) -> bool:
        upper = heading.upper()
        if upper.startswith("PROVINCE OF"):
            return True
        if upper.startswith("PRESIDENCY OF"):
            return True
        if upper.startswith("COLONY OF"):
            return True
        if upper.startswith("STATE OF"):
            return True
        if upper.startswith("THE DOMINION"):
            return True
        return False

    def _is_container_prefix(self, heading: str) -> bool:
        upper = heading.upper()
        for name, data in self.hierarchy.items():
            if upper == name:
                return True
            for alias in data.get("aliases", {}):
                if upper == alias:
                    return True
        return False

    def _select_canonical_name(self, variants: Sequence[str]) -> str:
        if not variants:
            return "UNKNOWN"
        if variants[0].upper().startswith("THE ") and len(variants) > 1:
            return variants[0].strip()
        first = variants[0].strip()
        if first.upper().startswith("PROVINCE OF ") and len(variants) > 1:
            return variants[-1].strip()
        return first

    def _format_heading(self, block: Block) -> str:
        variants = block.prefix_headings + [block.heading]
        return " › ".join(variant.strip() for variant in variants if variant.strip())

    def _valid_section_header(self, header: str) -> bool:
        if "|" in header:
            return False
        stripped = header[:-1]
        words = stripped.split()
        if not words:
            return False
        if len(stripped) > 80:
            return False
        capitalized_words = 0
        for word in words:
            clean = word.strip("-'")
            if not clean:
                return False
            if clean.lower() in LOWER_STOPWORDS:
                continue
            if not clean[0].isupper():
                return False
            capitalized_words += 1
        return capitalized_words >= 1

    def _normalize_section_title(self, header: str) -> str:
        cleaned = header.strip().rstrip(".").lower()
        return " ".join(cleaned.split())


def chunk_colonial_file(path: Path) -> Dict[str, Any]:
    return ColonialOfficeChunker().process_file(path)


__all__ = ["ColonialOfficeChunker", "chunk_colonial_file"]
