# Reference Quarantine Directory
# Governed by Specification 29 Section 4.3

Downloaded external datasets, raw outputs, or public reference materials enter here first.
Files must be validated for:
1. Permissive Open License
2. Non-executable format (CSV, Parquet, TSV, JSON)
3. SHA-256 integrity

Once validated via `tools/goldens/quarantine.py`, files are copied to `reference/sources/`.
