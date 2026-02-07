"""Shared fixtures and configuration for the test suite."""

import sys
from pathlib import Path

# Ensure the src directory is on the import path so that `from chunking.xxx`
# works regardless of how pytest is invoked.
ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Default data directories.  Tests that need real OCR files should skip
# gracefully when the data is absent (see the ``DATA_*`` sentinels in
# individual test modules).
TEST_SUBSET_DIR = ROOT / "data" / "test_subset"
EXTRACTED_JSON_DIR = ROOT / "extracted_json"
