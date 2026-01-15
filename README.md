# Goodreads Quotes Exporter

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Scrape Goodreads quotes by tag and export **separate CSV files per category** with clean formatting, de-duplication, and a polished terminal experience.

## Features

- Select tags via numbers, comma lists, or ranges (e.g., `1,3,5` or `2-8`)
- Per-tag CSV export in `Export/` (e.g., `Love.csv`, `Motivation.csv`)
- Global duplicate protection across all files
- Cleaned author names and quote text
- Stylish terminal progress bars

## Requirements

```bash
pip install -r requirements.txt
```

## Usage

```bash
python goodreads.py
```

### Select Categories

- `all` for every tag
- Comma list: `1,3,5`
- Range: `1-5`
- Mixed: `1,4-9,12`

### Pages

- Enter a number (e.g., `2`) for pages per category
- Use `0` for all pages

## Output Structure (CSV)

Each category exports to its own CSV with the same header:

| Column | Description |
| --- | --- |
| SNO | Serial number (auto-increment per file) |
| THUMB | Blank (reserved) |
| CATEGORY | Category name (deduped words) |
| AUTHOR | Clean author name |
| QUOTE | Clean quote text |
| TRANSLATE | Blank (reserved) |
| TAGS | Tags from Goodreads |
| LIKES | Likes count |
| IMAGE | Author image URL |
| TOTAL | Character count of quote |

## Available Categories

1. Love Quotes
2. Life Quotes
3. Inspirational Quotes
4. Humor Quotes
5. Philosophy Quotes
6. Inspirational Quotes Quotes
7. God Quotes
8. Truth Quotes
9. Wisdom Quotes
10. Romance Quotes
11. Poetry Quotes
12. Life Lessons Quotes
13. Death Quotes
14. Happiness Quotes
15. Hope Quotes
16. Faith Quotes
17. Inspiration Quotes
18. Spirituality Quotes
19. Relationships Quotes
20. Life Quotes Quotes
21. Motivational Quotes
22. Religion Quotes
23. Love Quotes Quotes
24. Writing Quotes
25. Success Quotes
26. Travel Quotes
27. Motivation Quotes
28. Time Quotes
29. Motivational Quotes Quotes

## Notes

- Random delays are used between requests to be polite
- Outputs append to existing CSVs if they already exist
- No Google Sheets export (local CSV only)

## Author

**Nadeem**  
Email: net2outlawzz@gmail.com  
Socials: @net2nadeem (YouTube, Instagram, Facebook)
