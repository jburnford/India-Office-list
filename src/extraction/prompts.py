"""Prompt templates for LLM-based entity extraction.

Each prompt is designed for a specific chunk format identified in the
India Office Lists.  The prompts include:
  - A role description and task framing
  - The abbreviation reference (injected at runtime)
  - Format-specific instructions with real examples
  - The output JSON schema

Prompts are kept as plain strings so they work with any LLM backend.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

_ABBREV_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "abbreviations.json"


def _load_abbreviations() -> str:
    """Load the abbreviation reference as a formatted string for prompt injection."""
    if _ABBREV_PATH.exists():
        data = json.loads(_ABBREV_PATH.read_text())
        lines = []
        for category, abbrevs in data.items():
            lines.append(f"## {category.replace('_', ' ').title()}")
            for abbr, expansion in abbrevs.items():
                lines.append(f"  {abbr} = {expansion}")
            lines.append("")
        return "\n".join(lines)
    return "(abbreviation reference not available)"


# ---------------------------------------------------------------------------
# Output schema description (shared across all prompts)
# ---------------------------------------------------------------------------

OUTPUT_SCHEMA = """\
Return a JSON object with this structure:

{
  "persons": [
    {
      "surname": "string (required)",
      "given_names": "string or null",
      "title": "string or null — e.g. Sir, Raja, Nawab, Sardar",
      "name_raw": "the full name exactly as it appears in the source",
      "degrees": ["B.A.", "M.A.", ...],
      "honours": [
        {"abbreviation": "C.S.I.", "expanded": "Companion of the Order of the Star of India", "date_awarded": "string or null"}
      ],
      "appointments": [
        {
          "role_raw": "the role as written in the source",
          "role_expanded": "the role with abbreviations expanded",
          "department": "string or null",
          "location": "string or null — place name as it appears",
          "year_appointed": "string or null — year from context",
          "date_start": "string or null — specific date if given",
          "is_acting": false,
          "is_officiating": false,
          "status": "string or null — e.g. on furlough, retired"
        }
      ],
      "confidence": "high | medium | low"
    }
  ],
  "locations": ["list of all distinct place names mentioned in this chunk"],
  "year_context": "string or null — the year heading if this chunk is organized by year"
}

IMPORTANT RULES:
- Extract EVERY person mentioned.  Do not skip anyone.
- Expand ALL abbreviations in role_expanded using the reference provided.
- Keep role_raw exactly as it appears in the source text.
- For name_raw, preserve the exact original text including punctuation.
- If a person appears with just a surname and initials, that is fine — do not guess full names.
- Indian titles like "Nawab", "Raja", "Sardar", "Kumar" go in the "title" field, not surname.
- Honours (C.S.I., K.C.I.E., etc.) go in the honours list, NOT in degrees.
- Degrees (B.A., M.A., M.B., LL.B., etc.) go in degrees, NOT in honours.
- If the chunk is organized by year (e.g. "1882." on its own line), set year_context and use it as year_appointed for entries under that year.
- Set confidence to "low" if the text is ambiguous, damaged by OCR, or you are unsure about parsing.
- Return valid JSON only.  No markdown, no commentary outside the JSON.
"""

# ---------------------------------------------------------------------------
# System prompt (shared context)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are a specialist in extracting structured biographical data from 19th-century \
British colonial administrative records.  You understand the conventions of the \
India Office Lists (1886–1899), including:
- Abbreviated titles, ranks, honours, and degrees
- The administrative geography of British India (presidencies, provinces, agencies)
- Name patterns for both European and Indian officials
- Career progression tracking by year of appointment

Your job is to extract every person mentioned in a text chunk into a structured \
JSON format, expanding abbreviations and preserving exact source text for provenance.

Here is a reference of common abbreviations used in these documents:

{abbreviations}
"""

# ---------------------------------------------------------------------------
# Format-specific prompts
# ---------------------------------------------------------------------------

ROSTER_ROLE_POSITION = """\
Extract all persons from this administrative roster chunk.

This chunk lists officials with their current positions.  The typical format is:
  Role—Name, Honours.
or:
  Role—Name, Honours, additional details.

EXAMPLE INPUT:
  Chief Secretary to Government—H. J. S. Cotton, C.S.I.
  Secretary, Financial and Municipal Departments—H. H. Risley, C.I.E.
  Under Secretary—N. Bonham-Carter.

EXAMPLE OUTPUT for the first entry:
{{
  "surname": "Cotton",
  "given_names": "H. J. S.",
  "title": null,
  "name_raw": "H. J. S. Cotton, C.S.I.",
  "degrees": [],
  "honours": [{{"abbreviation": "C.S.I.", "expanded": "Companion of the Order of the Star of India"}}],
  "appointments": [{{
    "role_raw": "Chief Secretary to Government",
    "role_expanded": "Chief Secretary to Government",
    "department": null,
    "location": null,
    "year_appointed": null
  }}],
  "confidence": "high"
}}

Context for this chunk:
- Volume: {volume}
- Section path: {section_path}

Now extract from this text:

{chunk_text}

{output_schema}
"""

ROSTER_YEAR_BASED = """\
Extract all persons from this career progression list organized by year.

The typical format is a year heading followed by entries:
  YEAR.
  Surname, Given Names, Honours, Degrees, Role, Location.

EXAMPLE INPUT:
  1861.
  Ward, W. E., C.S.I., M.A., Chief Commr., Assam.
  Stevens, C. C., C.S.I., B.A., Member Board of Revenue, Bengal.

EXAMPLE OUTPUT for the first entry:
{{
  "surname": "Ward",
  "given_names": "W. E.",
  "title": null,
  "name_raw": "Ward, W. E., C.S.I., M.A., Chief Commr., Assam.",
  "degrees": ["M.A."],
  "honours": [{{"abbreviation": "C.S.I.", "expanded": "Companion of the Order of the Star of India"}}],
  "appointments": [{{
    "role_raw": "Chief Commr.",
    "role_expanded": "Chief Commissioner",
    "department": null,
    "location": "Assam",
    "year_appointed": "1861"
  }}],
  "confidence": "high"
}}

Note: Each year heading (a line like "1861." or "1882.") applies to all entries below it
until the next year heading.

Context for this chunk:
- Volume: {volume}
- Section path: {section_path}

Now extract from this text:

{chunk_text}

{output_schema}
"""

ROSTER_MEDICAL_MILITARY = """\
Extract all persons from this military or medical roster.

Entries typically follow the pattern:
  Surname, Given Names, Honours, Degrees, Role/Specialty, Location.

Medical entries often include specialty information:
  King, George, C.I.E., M.B., F.R.S., Superintendent of the Royal Botanical Gardens, Calcutta.

Military entries may include regiment and rank:
  Commandant—Lt.Col W. R. E. Alexander, St. Corps, 5 Aug. 67

Pay attention to:
- Military ranks (Lt.-Col., Maj.-Gen., Brig.-Surg., etc.)
- Medical qualifications (M.B., M.D., F.R.C.S.)
- Dual roles (e.g. "Civil Surgeon and Superintendent of Lunatic Asylum")
- Dates of commission or appointment

Context for this chunk:
- Volume: {volume}
- Section path: {section_path}

Now extract from this text:

{chunk_text}

{output_schema}
"""

ROSTER_HONOURS = """\
Extract all persons from this honours or council list.

Entries list officials with their titles, decorations, and positions:
  Vice-President.—Sir Alfred Comyns Lyall, K.C.B., G.C.I.E.
  Field-Marshal Sir Donald M. Stewart, Bart., G.C.B., G.C.S.I., C.I.E.

Multiple honours are common.  Separate each into its own entry in the honours list.
Military ranks (Field-Marshal, Gen., Maj.-Gen.) should be extracted as part of the
appointment, not as a title.  "Sir" and "Bart." are titles.

Context for this chunk:
- Volume: {volume}
- Section path: {section_path}

Now extract from this text:

{chunk_text}

{output_schema}
"""

ROSTER_NATIVE_CIVIL = """\
Extract all persons from this list of Indian civil servants.

These entries feature Indian names with their own conventions:
  Sardar Gurdial Singh, Man., Dist. Judge, Punjab.
  Muhammad Afzal Khan, Nawab Khan Bahadur, Asst. Commr., Punjab.
  Kumar Gopendra Krishna Deb, M.A., Dist. and Sess. Judge, Bengal.

Pay special attention to:
- Indian titles: Sardar, Raja, Kumar, Kunwar, Nawab, Kazi, Saiyid/Syad go in "title"
- Honorifics: Khan Bahadur, Rai Bahadur are honours, not part of the name
- Compound given names: "Gopendra Krishna" is a given name, "Deb" is the surname
- Muslim names: "Muhammad Afzal Khan" — "Khan" can be surname or honorific; use context
- Year headings apply to entries below them

Context for this chunk:
- Volume: {volume}
- Section path: {section_path}

Now extract from this text:

{chunk_text}

{output_schema}
"""

NARRATIVE = """\
Extract all persons mentioned in this narrative text chunk.

This is not a structured roster — it is descriptive text about a department,
regulations, or administrative matter.  People may be mentioned in passing
or in descriptions of their roles.

Extract every named person with whatever information is available.
It is fine for many fields to be null if the text only mentions a name
without detailed career information.

Context for this chunk:
- Volume: {volume}
- Section path: {section_path}

Now extract from this text:

{chunk_text}

{output_schema}
"""

# ---------------------------------------------------------------------------
# Prompt selection
# ---------------------------------------------------------------------------

# Maps (chunk_type, heuristic) to prompt template
_PROMPT_TEMPLATES = {
    "roster_role_position": ROSTER_ROLE_POSITION,
    "roster_year_based": ROSTER_YEAR_BASED,
    "roster_medical_military": ROSTER_MEDICAL_MILITARY,
    "roster_honours": ROSTER_HONOURS,
    "roster_native_civil": ROSTER_NATIVE_CIVIL,
    "narrative": NARRATIVE,
}


def classify_roster_format(chunk: dict) -> str:
    """Heuristic to select the right roster prompt based on chunk content."""
    text = chunk.get("text", "")
    section_path = chunk.get("section_path", [])
    path_str = " ".join(section_path).upper()

    # Year-based: look for year headings (standalone 4-digit year lines)
    import re
    year_lines = re.findall(r"(?m)^\s*(?:18|19)\d{2}\.\s*$", text)
    if len(year_lines) >= 2:
        # Check for Indian names to pick the right sub-prompt
        if "NATIVE" in path_str or "STATUTORY" in path_str:
            return "roster_native_civil"
        return "roster_year_based"

    # Role—Name format: look for em-dashes separating role from name
    dash_lines = text.count("—")
    lines = text.strip().splitlines()
    if dash_lines >= 3 and dash_lines >= len(lines) * 0.3:
        return "roster_role_position"

    # Medical/military keywords
    medical_military_kw = {"SURGEON", "MEDICAL", "BRIGADE", "MILITARY", "REGIMENT",
                           "CAVALRY", "INFANTRY", "ARTILLERY", "ENGINEERS"}
    if any(kw in path_str for kw in medical_military_kw):
        return "roster_medical_military"

    # Honours/council
    honours_kw = {"COUNCIL", "KNIGHT", "ORDER", "COMPANIONS", "HONOURS"}
    if any(kw in path_str for kw in honours_kw):
        return "roster_honours"

    # Default: year-based is the most common roster format
    return "roster_year_based"


def build_prompt(
    chunk: dict,
    volume: str,
    abbreviations: Optional[str] = None,
) -> tuple[str, str]:
    """Build the system prompt and user prompt for a chunk.

    Returns (system_prompt, user_prompt).
    """
    if abbreviations is None:
        abbreviations = _load_abbreviations()

    system = SYSTEM_PROMPT.format(abbreviations=abbreviations)

    chunk_type = chunk.get("chunk_type", "narrative")
    if chunk_type == "roster":
        template_key = classify_roster_format(chunk)
    else:
        template_key = "narrative"

    template = _PROMPT_TEMPLATES[template_key]
    section_path = " > ".join(chunk.get("section_path", []))

    user = template.format(
        volume=volume,
        section_path=section_path,
        chunk_text=chunk.get("text", ""),
        output_schema=OUTPUT_SCHEMA,
    )

    return system, user
