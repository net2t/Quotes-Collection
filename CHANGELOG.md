# Changelog

## 2026-01-15

### Added

- Per-tag CSV export (one file per category).
- Rich-based terminal UI with tag selection ranges and progress bars.
- Global duplicate prevention across all CSV files.
- CSV schema with SNO, THUMB, CATEGORY, AUTHOR, QUOTE, TRANSLATE, TAGS, LIKES, IMAGE, TOTAL.

### Changed

- Cleaned author names and quote text to remove punctuation noise.
- Category normalization for repeated words ("Quotes Quotes" → "Quotes").
- Local CSV export only (removed Google Sheets export).
