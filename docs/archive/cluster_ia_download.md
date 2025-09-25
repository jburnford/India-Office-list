# Archive.org Bulk Download Project

## Overview

This project downloads and processes historical journal PDFs from Archive.org using the NIBI cluster infrastructure. The pipeline includes bulk PDF downloading, metadata extraction, and OCR text processing for research analysis.

## Project Goals

- Download ~21,901 PDFs from Archive.org JSTOR collections (1750-2019)
- Extract metadata mappings for each PDF
- Process PDFs through OCR pipeline (olm-ocr)
- Create searchable text corpus for historical research

## Directory Structure

```
/home/jic823/projects/def-jic823/pdf/
├── internet_archive/           # Scripts and tools
│   ├── archive_cluster_downloader.py
│   ├── restart_download.sh
│   ├── check_progress.sh
│   └── run_archive_download.sh
├── *.pdf                      # Downloaded PDF files
├── download_*.log             # Download logs
├── archive_download_*.out     # SLURM output logs
├── download_progress.json     # Progress tracking
└── archive_metadata.json     # Metadata mappings (when created)
```

## Archive.org Search

**Target Collections:**
- jstor_botanicalgazette
- jstor_philtranroyasoc3
- jstor_jinfedise
- jstor_procroyasocilon3
- jstor_procria1836
- jstor_jroyageogsocilon
- jstor_jsociarts
- jstor_geogrevi
- jstor_procroyageogsoc2
- jstor_tranroyairisacad
- jstor_abstpapecommroya
- jstor_americanjbotany
- jstor_jroyasiasocgrbi
- jstor_economicbulletin
- jstor_anthrevi
- jstor_tranrasgrbritire
- jstor_thesoil
- jstor_botabull
- jstor_jethnsocilond184
- jstor_jethnsocilond186
- jstor_trananthsocilond

**Search Parameters:**
- Date range: 1750-2019
- Format: PDF
- Total results: ~21,901 documents

**Original Search URL:**
```
https://archive.org/details/jstor_ejc?and%5B%5D=collection%3A%22jstor_botanicalgazette%22&and%5B%5D=collection%3A%22jstor_philtranroyasoc3%22&and%5B%5D=collection%3A%22jstor_jinfedise%22&and%5B%5D=collection%3A%22jstor_procroyasocilon3%22&and%5B%5D=collection%3A%22jstor_procria1836%22&and%5B%5D=collection%3A%22jstor_jroyageogsocilon%22&and%5B%5D=collection%3A%22jstor_jsociarts%22&and%5B%5D=collection%3A%22jstor_geogrevi%22&and%5B%5D=collection%3A%22jstor_procroyageogsoc2%22&and%5B%5D=collection%3A%22jstor_tranroyairisacad%22&and%5B%5D=collection%3A%22jstor_abstpapecommroya%22&and%5B%5D=collection%3A%22jstor_americanjbotany%22&and%5B%5D=collection%3A%22jstor_jroyasiasocgrbi%22&and%5B%5D=collection%3A%22jstor_economicbulletin%22&and%5B%5D=collection%3A%22jstor_anthrevi%22&and%5B%5D=collection%3A%22jstor_tranrasgrbritire%22&and%5B%5D=collection%3A%22jstor_thesoil%22&and%5B%5D=collection%3A%22jstor_botabull%22&and%5B%5D=collection%3A%22jstor_jethnsocilond184%22&and%5B%5D=collection%3A%22jstor_jethnsocilond186%22&and%5B%5D=collection%3A%22jstor_trananthsocilond%22&and%5B%5D=year%3A%5B1750+TO+2019%5D
```

## Scripts and Tools

### 1. Download Script (`archive_cluster_downloader.py`)

**Purpose:** Bulk download PDFs from Archive.org using API

**Features:**
- Robust error handling and retries
- Progress tracking and resumability
- Prefers color PDFs over black-and-white
- Rate limiting (0.05s delay)
- Signal handling for graceful shutdown

**Usage:**
```bash
python3 archive_cluster_downloader.py --download-dir /path/to/pdfs --delay 0.05
```

### 2. Job Management Scripts

**`run_archive_download.sh`** - SLURM job submission script
- 48-hour time limit
- 16GB memory allocation
- Email notifications

**`restart_download.sh`** - Smart restart utility
- Checks current progress
- Cancels running jobs if needed
- Resubmits with current settings

**`check_progress.sh`** - Progress monitoring
- Shows download statistics
- Disk usage tracking
- Recent log entries

### 3. Metadata Collection (`get_archive_metadata.py`)

**Purpose:** Create JSON mapping from PDF identifiers to full metadata

**Features:**
- Filters for numeric Archive.org identifiers only
- Progress saving every 50 items
- Resumable on interruption
- Rate limited API calls

**Usage:**
```bash
python3 get_archive_metadata.py /path/to/pdf/directory
```

## Workflow

### Phase 1: Download PDFs
1. Submit download job: `./restart_download.sh`
2. Monitor progress: `./check_progress.sh`
3. Resume if needed: `./restart_download.sh`

### Phase 2: Extract Metadata
1. Run metadata collection: `python3 get_archive_metadata.py .`
2. Creates `archive_metadata.json` mapping file

### Phase 3: OCR Processing
1. Upload PDFs to OCR processing system (olm-ocr)
2. Process in batches to create JSONL files
3. Extract individual JSON files per PDF

## File Naming and Identification

**PDF Files:** Numeric Archive.org identifiers
- Example: `3206270938.pdf`, `3200811905.pdf`

**Metadata Mapping:** JSON structure
```json
{
  "3206270938": {
    "metadata": {
      "title": "Document Title",
      "creator": "Author Name",
      "date": "1875",
      // ... full Archive.org metadata
    }
  }
}
```

**OCR Results:** JSONL with source file references
```json
{
  "id": "unique_id",
  "text": "OCR extracted text...",
  "metadata": {
    "Source-File": "/path/3206270938.pdf"
  }
}
```

## Progress Tracking

**Current Status (as of Sept 19, 2025):**
- Target: ~21,901 PDFs
- Downloaded: 200 new files
- Skipped: 9,800 (existing files)
- Total in directory: ~939 files (mixed content)

**Progress File:** `download_progress.json`
```json
{
  "downloaded": 200,
  "failed": 0,
  "skipped": 9800,
  "last_update": "2025-09-19T01:25:38.497465"
}
```

## Troubleshooting

### Issue: High Skip Count
**Problem:** Script reports skipping 9,800 files but directory only has ~939 items
**Cause:** Search returning different identifier formats than expected
**Solution:** Verify search query matches original Archive.org search

### Issue: Wrong Identifier Format
**Problem:** Getting `jstor-106324` instead of `3206270938`
**Cause:** Search query pulling different collection items
**Solution:** Update search query to match exact original parameters

### Issue: Job Timeout
**Problem:** 48-hour job limit reached
**Solution:** Use restart script - automatically resumes from last position

### Issue: Missing PDFs
**Problem:** Some Archive.org items don't have downloadable PDFs
**Expected:** Not all items in search results have PDF files available

## Monitoring Commands

```bash
# Check job status
squeue -u jic823

# Monitor progress
./check_progress.sh

# View recent logs
tail -f download_*.log
tail -f archive_download_*.out

# Count files
ls *.pdf | wc -l                    # All PDFs
ls [0-9]*.pdf | wc -l              # Numeric Archive.org PDFs only

# Cancel running job
scancel <job_id>
```

## Integration with OCR Pipeline

**Input:** PDF files with numeric identifiers
**Processing:** olm-ocr batch processing
**Output:** JSONL files with:
- OCR extracted text
- Processing metadata
- Source file references

**Connection Point:** PDF filename serves as key to connect:
1. PDF file (`3206270938.pdf`)
2. Archive.org metadata (`archive_metadata.json["3206270938"]`)
3. OCR results (JSONL with `"Source-File": "...3206270938.pdf"`)

## Next Steps

1. **Fix search query** to ensure numeric identifiers
2. **Complete PDF downloads** using corrected script
3. **Generate metadata mappings** for all downloaded PDFs
4. **Process through OCR pipeline** in batches
5. **Create unified dataset** combining PDFs, metadata, and OCR text

## Resource Requirements

**Storage:** Several hundred GB for full collection
**Compute:** SLURM jobs with 16GB RAM, 4 CPUs
**Network:** Sustained downloads from Archive.org
**Time:** Estimated 24-48 hours for full collection (depends on network speed)

## Notes

- Archive.org is designed for bulk access - no need for excessive rate limiting
- Color PDFs preferred over black-and-white versions
- Progress tracking allows for interruption and resumption
- Mixed directory contains other PDF collections - scripts filter appropriately