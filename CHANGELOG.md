# Changelog

## Unreleased

- Added `get_variable_metadata`, which parses a tabular file's DDI codebook XML into variable labels, value labels, question text, universe, type, interval, notes, weight flag, variable groups, and summary statistics. Supports `name_filter` and `offset` paging, validates numeric file IDs, caps codebook size (`BOREALIS_MAX_DDI_BYTES`), and refuses XML with DOCTYPE/ENTITY declarations.
- Added `assess_metadata_quality`, which scores a dataset's DDI metadata completeness (0-100, letter grade) against a 15-field rubric and returns prioritized recommendations for missing fields. Fields are matched by exact local name (so `title` is not confused with `alternativeTitle`). The optional variable check pools label/value-label/question-text coverage across up to `max_files_checked` tabular files for partial credit, and both halves read the same requested `version` (default `:latest-published`).
- `get_dataset_metadata` accepts an optional `version`.
- Added a `tabular` flag to `list_dataset_files` output.

## 0.3.0 — Borealis Research Toolkit refactor

- Split Borealis API access, research logic, transports, configuration, and institution mappings into modules.
- Added structured results with provenance and warnings.
- Added stdio MCP and Streamable HTTP MCP entry points.
- Added an optional FastAPI REST interface.
- Added bounded streaming file downloads and partial line retrieval.
- Added CSV/TSV profiling with explicit interpretation warnings.
- Added Docker, Compose, environment template, GitHub Actions, and architecture documentation.
- Kept `borealis_server.py` as a backward-compatible local entry point.

## 0.2.0

- Added dataset-only defaults, pagination, date filters, diagnostics, and initial tabular profiling.
