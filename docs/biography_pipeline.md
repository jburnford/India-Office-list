# Biography Extraction & Knowledge-Graph Plan

This note summarises how we are handling the "DESCRIPTION OF SERVICES" /
"RECORD OF SERVICES" sections in the India Office Lists (1886–1899) and how
we intend to turn them into a knowledge graph.

## 1. Source coverage
- First appearance: `iacsl_1886_supp`
- Last confirmed: `iliol_1899`
- Total entries extracted so far: 11,835 (see `biography_entries.json`)

The extraction script currently looks for section titles containing
"DESCRIPTION OF SERVICES" or "RECORD OF SERVICES". If additional headings are
found in later volumes, add them to `BIO_PATTERNS` inside the script.

## 2. Splitting strategy
Biographies inside those sections follow a predictable pattern of uppercase
surname headings. We split on `^[A-Z][A-Z'\- ]+,` at the beginning of a line and
capture everything until the next uppercase heading. The result is a JSON entry
with:

- `volume`: source file stem (e.g., `iacsl_1890_supp.chunks`)
- `section_title`: heading text (`DESCRIPTION OF SERVICES` or `RECORD OF SERVICES`)
- `section_path`: chunk path for additional context (province/residency)
- `name_heading`: uppercase heading (e.g., `CURZON, GEORGE N.`)
- `entry_text`: cleaned biography paragraph(s)

## 3. LLM extraction plan
For each entry we will prompt an LLM to extract structured facts.  Target fields
include:
- canonical person name and variants
- ranks, appointments, departments, honours (with start/end dates where given)
- locations (posting, birthplace, education, etc.)
- notes (exam results, deputations, special missions)

Every fact must carry provenance: `(volume, chunk/section path, quote snippet)`
so we can trace it back to the primary source.

## 4. Cross-year identity resolution
When moving from year N to year N+1 we will:
1. Retrieve the canonical person record (if any) from year N
2. Provide that record as context to the LLM together with the new biography
3. Ask the model to confirm the match and list differences/new facts
4. Update the canonical record while keeping the provenance history per fact

We will store confidence scores and rationales for each match so that manual
reviews can focus on ambiguous cases.

## 5. Grounding & graph nodes
- **People**: maintain a local identifier; later, match against Wikidata when
  possible.
- **Places/Institutions**: collect candidates during extraction and run a
  separate grounding step (LLM or rules) to assign GeoNames/Wikidata PIDs.
- **Edges**: expected relations include `held_position`, `served_in`,
  `posted_to`, `member_of`, `awarded`, etc.

## 6. Next actions
- Finalise the per-entry extraction script (see `scripts/build_biography_entries.py`)
- Design the LLM prompt format for individual entries and for cross-year updates
- Create storage schemas for canonical officer records and fact provenance
- Prototype the grounding helper

