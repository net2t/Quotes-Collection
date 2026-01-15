# Changelog

## 2026-01-15

### Added

- Per-tag CSV export (one file per category).
- Rich-based terminal UI with tag selection ranges and progress bars.
- Global duplicate prevention across all CSV files.
- CSV schema with SNO, THUMB, CATEGORY, AUTHOR, QUOTE, TRANSLATE, TAGS, LIKES, IMAGE, TOTAL.
- Google Sheets export via secrets with scheduled GitHub Actions workflow.

### Changed

- Cleaned author names and quote text to remove punctuation noise.
- Category normalization for repeated words ("Quotes Quotes" → "Quotes").
- CSV export remains primary; Google Sheets is optional via secrets.
