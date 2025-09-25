# India Office List Processing Toolkit

This repository collects the scripts and documentation we are using to
structure the India Office / India Civil Service Lists for downstream
knowledge-graph work.  The tooling grew out of earlier smart chunking
experiments for the Colonial Office Lists and now includes:

- robust chunkers in `src/chunking/` for both colonial and India Office
  volumes
- utilities (archived in `scripts/legacy/`) that originally handled
  downloading and OCR extraction
- unit tests under `tests/` and root-level `test_*.py` files
- JSON summaries and chunk outputs that are generated locally and kept out
  of git via `.gitignore`

## Repository layout

```
results/
├── README.md                # this document
├── .gitignore
├── docs/
│   └── archive/             # historical notes and summaries from earlier work
├── scripts/
│   └── legacy/              # download/extraction utilities kept for reference
├── src/
│   └── chunking/
│       ├── colonial_office_chunker.py
│       └── india_office_chunker.py
├── tests/                   # pytest suite for extraction modules
├── test_*.py                # convenience wrappers for individual runs
└── chunks/ & *.json         # generated artefacts (ignored by git)
```

The heavy JSON data files (`*.json`, `chunks/`, etc.) remain on disk but are
ignored in git.  Regenerate them with the scripts described below when
needed.

## India Office chunking workflow

1. **Create the list of source files**
   ```bash
   python scripts/legacy/get_archive_metadata.py  # updates file manifests
   ```
   or build your own list; we currently keep it in
   `india_office_file_list.json` (ignored in git).

2. **Run the chunker**
   ```bash
   python - <<'PY'
   import json
   from pathlib import Path
   from chunking.india_office_chunker import IndiaOfficeChunker

   chunker = IndiaOfficeChunker()
   path = Path('il_1892_jan.json')
   data = json.loads(path.read_text())
   result = chunker.chunk_text(data['text'], data.get('attributes'))
   Path('chunks/il_1892_jan.chunks.json').write_text(json.dumps(result, indent=2))
   PY
   ```
   Each call produces `chunks/<volume>.chunks.json` containing an array of
   chunks with `section_path`, `chunk_type`, page ranges, and text.

3. **Extract biographical entries**
   We consolidated all “DESCRIPTION OF SERVICES” and “RECORD OF SERVICES”
   sections into `biography_entries.json` (ignored by git).  Recreate it with
   `python scripts/build_biography_entries.py` (see below).

## Biography pipeline

- **Input volumes**: Biographies first appear in the 1886 supplement and run
  through the 1899 “India List and India Office List”.
- **Extraction script**: `scripts/build_biography_entries.py` (added as part of
  this cleanup) scans the chunk files, splits each biography by uppercase
  heading, and writes the per-officer JSON.
- **Output**: `biography_entries.json` with 11,835 entries, each carrying the
  source volume, section path, uppercase heading, and clean text.

We keep the extraction script under version control; rerun it whenever you
update the chunk files.

## Future steps

The next milestones (to be tracked in code soon):

- LLM prompts to parse each biography into structured facts and link them to
  existing nodes when processing later years
- GeoNames/Wikidata grounding helpers for places and institutions detected in
  the biographies
- Persistence layer for the canonical officer records with provenance for
  every fact

See `docs/biography_pipeline.md` for the current plan.

