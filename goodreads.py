#!/usr/bin/env python3
"""
Goodreads Quotes Scraper
Scrapes quotes from Goodreads tag pages and exports them to a single CSV file.
"""

import requests
import time
import random
import sys
import signal
import csv
import re
import os
import json
import base64
from pathlib import Path
from bs4 import BeautifulSoup
from typing import List, Tuple, Set, Dict
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.prompt import Prompt
from rich.table import Table
import gspread
from google.oauth2.service_account import Credentials

# Configuration
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
REQUEST_TIMEOUT = 30
MAX_PAGES_PER_CATEGORY = 100


# Tag data
RAW_TAG_TABLE = [
    (1, "Love Quotes", "https://www.goodreads.com/quotes/tag/love"),
    (2, "Life Quotes", "https://www.goodreads.com/quotes/tag/life"),
    (3, "Inspirational Quotes", "https://www.goodreads.com/quotes/tag/inspirational"),
    (4, "Humor Quotes", "https://www.goodreads.com/quotes/tag/humor"),
    (5, "Philosophy Quotes", "https://www.goodreads.com/quotes/tag/philosophy"),
    (6, "Inspirational Quotes Quotes", "https://www.goodreads.com/quotes/tag/inspirational-quotes"),
    (7, "God Quotes", "https://www.goodreads.com/quotes/tag/god"),
    (8, "Truth Quotes", "https://www.goodreads.com/quotes/tag/truth"),
    (9, "Wisdom Quotes", "https://www.goodreads.com/quotes/tag/wisdom"),
    (10, "Romance Quotes", "https://www.goodreads.com/quotes/tag/romance"),
    (11, "Poetry Quotes", "https://www.goodreads.com/quotes/tag/poetry"),
    (12, "Life Lessons Quotes", "https://www.goodreads.com/quotes/tag/life-lessons"),
    (13, "Death Quotes", "https://www.goodreads.com/quotes/tag/death"),
    (14, "Happiness Quotes", "https://www.goodreads.com/quotes/tag/happiness"),
    (15, "Hope Quotes", "https://www.goodreads.com/quotes/tag/hope"),
    (16, "Faith Quotes", "https://www.goodreads.com/quotes/tag/faith"),
    (17, "Inspiration Quotes", "https://www.goodreads.com/quotes/tag/inspiration"),
    (18, "Spirituality Quotes", "https://www.goodreads.com/quotes/tag/spirituality"),
    (19, "Relationships Quotes", "https://www.goodreads.com/quotes/tag/relationships"),
    (20, "Life Quotes Quotes", "https://www.goodreads.com/quotes/tag/life-quotes"),
    (21, "Motivational Quotes", "https://www.goodreads.com/quotes/tag/motivational"),
    (22, "Religion Quotes", "https://www.goodreads.com/quotes/tag/religion"),
    (23, "Love Quotes Quotes", "https://www.goodreads.com/quotes/tag/love-quotes"),
    (24, "Writing Quotes", "https://www.goodreads.com/quotes/tag/writing"),
    (25, "Success Quotes", "https://www.goodreads.com/quotes/tag/success"),
    (26, "Travel Quotes", "https://www.goodreads.com/quotes/tag/travel"),
    (27, "Motivation Quotes", "https://www.goodreads.com/quotes/tag/motivation"),
    (28, "Time Quotes", "https://www.goodreads.com/quotes/tag/time"),
    (29, "Motivational Quotes Quotes", "https://www.goodreads.com/quotes/tag/motivational-quotes"),
]

console = Console(emoji=False)

def clean_tags(tags: str) -> str:
    """Clean tags by removing 'tags:' prefix and making comma-separated."""
    if not tags:
        return ""
    
    # Remove 'tags:' prefix if present
    if tags.startswith("tags:"):
        tags = tags[5:].strip()  # Remove 'tags:' prefix
    
    # Split by comma and clean each tag
    tag_list = [tag.strip() for tag in tags.split(',')]
    
    # Filter out empty tags and join with comma
    clean_tag_list = [tag for tag in tag_list if tag]
    
    return ', '.join(clean_tag_list)

def clean_text(text: str) -> str:
    """Clean quote text by removing attribution, normalizing special characters, and cleaning whitespace."""
    if not text:
        return ""

    # 1. Remove author attribution and trailing text (like "- J.K. Rowling, The ...")
    # This is often separated by a long dash.
    text = re.split(r'\s*[-—–―]+\s*', text, maxsplit=1)[0]

    # 2. Normalize Unicode characters to their closest ASCII equivalent
    # This handles curly quotes, special dashes, ellipses, etc.
    text = text.replace('“', '"').replace('”', '"')  # Double quotes
    text = text.replace('‘', "'").replace('’', "'")  # Single quotes
    text = text.replace('…', '...')              # Ellipsis
    text = text.replace('–', '-')                # En dash
    text = text.replace('—', '-')                # Em dash

    # 3. Remove any remaining non-ASCII characters
    # This is a fallback for any other strange characters.
    text = text.encode('ascii', 'ignore').decode('utf-8')

    # 4. Strip leading/trailing quotes and whitespace
    text = text.strip()
    text = text.strip('"\'')

    # 5. Remove noisy punctuation at the edges
    text = re.sub(r"^[\s,.:;-]+", "", text)
    text = re.sub(r"[\s,.:;-]+$", "", text)

    # 6. Clean up whitespace
    text = ' '.join(text.split())

    return text

def clean_author_name(text: str) -> str:
    """Clean author name by removing punctuation and extra whitespace."""
    if not text:
        return "Unknown"
    text = text.strip().strip('"\'')
    text = re.sub(r"[=,\.-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or "Unknown"

def normalize_category(name: str) -> str:
    if not name:
        return ""
    name = re.sub(r"\s+", " ", name).strip()
    name = re.sub(r"\b(Quotes|Quote)\s+\1\b", r"\1", name, flags=re.IGNORECASE)
    return name

def category_to_filename(name: str) -> str:
    clean = normalize_category(name)
    clean = re.sub(r"\bQuotes\b", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean or "Quotes"

def quote_key(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()

def env_value(name: str) -> str:
    return os.getenv(name, "").strip()

def parse_service_account_json(raw_value: str) -> dict:
    if not raw_value:
        return {}
    raw_value = raw_value.strip()
    try:
        if raw_value.startswith("{"):
            return json.loads(raw_value)
        decoded = base64.b64decode(raw_value).decode("utf-8")
        return json.loads(decoded)
    except Exception:
        return {}

def load_sheet_client() -> gspread.Client | None:
    sheet_json = env_value("GOODREADS_SERVICE_ACCOUNT_JSON")
    sheet_info = parse_service_account_json(sheet_json)
    if not sheet_info:
        return None
    credentials = Credentials.from_service_account_info(
        sheet_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    return gspread.authorize(credentials)

def load_existing_sheet_quotes(worksheet) -> Tuple[Set[str], int]:
    existing: Set[str] = set()
    last_sno = 0
    try:
        rows = worksheet.get_all_records()
        for row in rows:
            quote_value = row.get("QUOTE")
            if quote_value:
                existing.add(quote_key(str(quote_value)))
            sno_value = str(row.get("SNO", "")).strip()
            if sno_value.isdigit():
                last_sno = max(last_sno, int(sno_value))
    except Exception:
        return existing, last_sno

def ensure_sheet_header_format(worksheet) -> None:
    try:
        worksheet.freeze(rows=1)
        worksheet.format(
            "1:1",
            {
                "horizontalAlignment": "CENTER",
                "textFormat": {"bold": True},
            },
        )
    except Exception:
        return

def extract_likes(quote_div) -> int:
    """Extract likes count from quote div."""
    try:
        likes_div = quote_div.find("div", class_="right")
        if likes_div:
            likes_text = likes_div.get_text(strip=True)
            if "likes" in likes_text:
                likes_num = likes_text.split("likes")[0].strip().replace(",", "")
                return int(likes_num) if likes_num.isdigit() else 0
        return 0
    except:
        return 0

def extract_author_image(quote_div) -> str:
    """Extract author image URL."""
    try:
        img_tag = quote_div.find("img")
        if img_tag and img_tag.get("src"):
            return img_tag.get("src")
        return ""
    except:
        return ""

def fetch(url: str, session: requests.Session) -> requests.Response | None:
    """Fetch a URL with proper headers and error handling."""
    try:
        headers = {"User-Agent": USER_AGENT}
        resp = session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp
    except Exception as e:
        print(f"Request failed: {e}")
        return None

def parse_page(soup: BeautifulSoup) -> List[Tuple[str, str, str, str, int]]:
    """Parse a quotes page from a BeautifulSoup object and extract quote data."""
    quotes = []
    
    for quote_div in soup.find_all("div", class_="quote"):
        try:
            quote_text = quote_div.find("div", class_="quoteText")
            if not quote_text:
                continue
                
            quote = clean_text(quote_text.get_text(strip=True))

            author_span = quote_div.find("span", class_="authorOrTitle")
            author = clean_author_name(author_span.get_text(strip=True)) if author_span else "Unknown"
            
            tags_div = quote_div.find("div", class_="greyText")
            tags = clean_tags(tags_div.get_text(strip=True)) if tags_div else ""
            
            img_url = extract_author_image(quote_div)
            likes = extract_likes(quote_div)
            
            if quote and len(quote) > 10:  # Filter out very short quotes
                quotes.append((quote, author, tags, img_url, likes))
                
        except Exception as e:
            print(f"Error parsing quote: {e}")
            continue
            
    return quotes

def find_next_page(soup: BeautifulSoup) -> str | None:
    """Find the URL of the next page using its class."""
    next_link = soup.find("a", class_="next_page")
    return next_link.get("href") if next_link else None






def parse_tag_selection(choice: str, max_number: int) -> List[int]:
    selected: Set[int] = set()
    if not choice:
        return []
    for part in choice.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            try:
                start_str, end_str = part.split("-", 1)
                start, end = int(start_str), int(end_str)
            except ValueError:
                return []
            if start > end:
                start, end = end, start
            for num in range(start, end + 1):
                if 1 <= num <= max_number:
                    selected.add(num)
        elif part.isdigit():
            num = int(part)
            if 1 <= num <= max_number:
                selected.add(num)
            else:
                return []
        else:
            return []
    return sorted(selected)

def show_tag_menu() -> List[int]:
    """Display tag selection menu and return chosen tag numbers."""
    table = Table(title="Goodreads Tag Selector", show_lines=True)
    table.add_column("No.", justify="right", style="bold cyan")
    table.add_column("Tag", style="bold white")
    for num, name, _ in RAW_TAG_TABLE:
        table.add_row(str(num), normalize_category(name))
    console.print(table)

    while True:
        choice = Prompt.ask(
            "Select tags [all | 1,3,5 | 1-5 | 1,4-9]",
            default="all",
        ).strip().lower()
        if choice == "all":
            return [item[0] for item in RAW_TAG_TABLE]

        chosen_numbers = parse_tag_selection(choice, len(RAW_TAG_TABLE))
        if chosen_numbers:
            return chosen_numbers

        console.print("[red]Invalid input.[/] Use commas or ranges like 1-5.")

def ask_page_limit() -> int:
    """Ask user for the number of pages to scrape per category."""
    while True:
        pages_str = Prompt.ask("How many pages per category? (0 = all)", default="1").strip()
        if pages_str.isdigit():
            pages = int(pages_str)
            if pages >= 0:
                return pages
        console.print("[red]Please enter a non-negative whole number.[/]")

def resolve_tag_selection() -> List[int]:
    env_choice = env_value("TAG_SELECTION")
    if env_choice:
        if env_choice.lower() == "all":
            return [item[0] for item in RAW_TAG_TABLE]
        parsed = parse_tag_selection(env_choice, len(RAW_TAG_TABLE))
        if parsed:
            return parsed
    if not sys.stdin.isatty():
        return [item[0] for item in RAW_TAG_TABLE]
    return show_tag_menu()

def resolve_page_limit() -> int:
    env_pages = env_value("PAGE_LIMIT")
    if env_pages.isdigit():
        return int(env_pages)
    if not sys.stdin.isatty():
        return 0
    return ask_page_limit()

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    print("\n\n⚠️  Script interrupted by user!")
    print("🔄 Saving current progress...")
    # You could add cleanup code here if needed
    sys.exit(0)

# CSV Header
CSV_HEADER = ["SNO", "THUMB", "CATEGORY", "AUTHOR", "QUOTE", "TRANSLATE", "TAGS", "LIKES", "IMAGE", "TOTAL"]

def load_existing_quotes(csv_path: Path) -> Tuple[Set[str], int]:
    """Load existing quotes from a CSV file to prevent duplicates and get last SNO."""
    if not csv_path.exists():
        return set(), 0
    
    existing_quotes: Set[str] = set()
    last_sno = 0
    try:
        with open(csv_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'QUOTE' in row and row['QUOTE']:
                    existing_quotes.add(quote_key(row['QUOTE']))
                if 'SNO' in row and row['SNO'].isdigit():
                    last_sno = max(last_sno, int(row['SNO']))
    except (FileNotFoundError, KeyError, Exception) as e:
        console.print(f"[yellow]Could not read existing CSV file:[/] {e}")

    return existing_quotes, last_sno

def main():
    """Main function to scrape quotes and save to a single CSV file."""
    signal.signal(signal.SIGINT, signal_handler)

    console.print(Panel.fit("[bold cyan]Goodreads Quotes Exporter[/]", border_style="cyan"))
    
    # --- User Input ---
    chosen_numbers = resolve_tag_selection()
    if not chosen_numbers:
        print("❌ No tags selected. Exiting.")
        return
    page_limit = resolve_page_limit()

    # --- File Setup ---
    out_dir = Path("Export")
    out_dir.mkdir(exist_ok=True)

    # --- Duplicate Check ---
    tags_to_scrape = [tag for tag in RAW_TAG_TABLE if tag[0] in chosen_numbers]
    file_states: Dict[Path, Dict[str, object]] = {}
    global_existing: Set[str] = set()
    sheet_states: Dict[str, Dict[str, object]] = {}
    sheet_client = load_sheet_client()
    sheet_url = env_value("GOODREADS_SHEET_URL")
    sheet_enabled = sheet_client is not None and bool(sheet_url)
    spreadsheet = None
    if sheet_enabled:
        try:
            spreadsheet = sheet_client.open_by_url(sheet_url)
        except Exception as exc:
            console.print(f"[yellow]Google Sheet disabled:[/] {exc}")
            sheet_enabled = False
    for _, tag_name, _ in tags_to_scrape:
        file_name = f"{category_to_filename(tag_name)}.csv"
        csv_path = out_dir / file_name
        existing_quotes, last_sno = load_existing_quotes(csv_path)
        file_states[csv_path] = {"existing": existing_quotes, "sno": last_sno}
        global_existing.update(existing_quotes)
        if sheet_enabled and spreadsheet is not None:
            sheet_title = category_to_filename(tag_name)
            try:
                worksheet = spreadsheet.worksheet(sheet_title)
            except Exception:
                worksheet = spreadsheet.add_worksheet(title=sheet_title, rows=1000, cols=len(CSV_HEADER))
            if worksheet.get_all_values() == []:
                worksheet.append_row(CSV_HEADER)
                ensure_sheet_header_format(worksheet)
            sheet_existing, sheet_last_sno = load_existing_sheet_quotes(worksheet)
            sheet_states[sheet_title] = {"existing": sheet_existing, "sno": sheet_last_sno, "sheet": worksheet}
            global_existing.update(sheet_existing)
    console.print(f"Loaded [bold]{len(global_existing)}[/] existing quotes across {len(file_states)} files.")

    # --- Scraping ---
    session = requests.Session()
    total_new_quotes = 0

    console.print(f"\nStarting scrape for [bold]{len(tags_to_scrape)}[/] categories...")

    try:
        progress = Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            BarColumn(bar_width=32),
            TextColumn("{task.completed}/{task.total}"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console,
        )
        with progress:
            overall_task = progress.add_task("Overall categories", total=len(tags_to_scrape))

            for _, tag_name, tag_url in tags_to_scrape:
                display_name = normalize_category(tag_name)
                file_name = f"{category_to_filename(tag_name)}.csv"
                csv_path = out_dir / file_name
                state = file_states[csv_path]
                existing_quotes = state["existing"]
                last_sno = state["sno"]
                sheet_state = None
                if sheet_enabled:
                    sheet_state = sheet_states.get(category_to_filename(tag_name))

                cur_url = tag_url
                pages_done = 0
                quotes_in_cat = 0
                page_total = page_limit if page_limit > 0 else None
                page_task = progress.add_task(f"[cyan]{display_name}[/]", total=page_total)
                new_sheet_rows: List[List[object]] = []

                with open(csv_path, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    if f.tell() == 0:
                        writer.writerow(CSV_HEADER)

                    while cur_url and (page_limit == 0 or pages_done < page_limit):
                        time.sleep(random.uniform(1, 2.5))

                        resp = fetch(cur_url, session)
                        if resp is None:
                            progress.update(page_task, description=f"[red]{display_name} (request failed)[/]")
                            break

                        soup = BeautifulSoup(resp.text, "lxml")
                        page_quotes = parse_page(soup)

                        new_on_page = 0
                        for quote, author, tags, img_url, likes in page_quotes:
                            normalized_quote = quote_key(quote)
                            if normalized_quote not in global_existing:
                                last_sno += 1
                                row_data = [
                                    last_sno,
                                    "",
                                    normalize_category(tag_name),
                                    author,
                                    quote,
                                    "",
                                    tags,
                                    likes,
                                    img_url,
                                    len(quote),
                                ]
                                writer.writerow(row_data)
                                existing_quotes.add(normalized_quote)
                                global_existing.add(normalized_quote)
                                if sheet_state is not None:
                                    new_sheet_rows.append(row_data)
                                new_on_page += 1

                        if new_on_page > 0:
                            quotes_in_cat += new_on_page
                            total_new_quotes += new_on_page

                        pages_done += 1
                        progress.update(page_task, advance=1, description=f"[cyan]{display_name}[/] ({quotes_in_cat} new)")

                        nxt = find_next_page(soup)
                        cur_url = f"https://www.goodreads.com{nxt}" if nxt else None

                state["sno"] = last_sno
                if sheet_state is not None and new_sheet_rows:
                    sheet_state["sno"] = last_sno
                    worksheet = sheet_state["sheet"]
                    worksheet.append_rows(new_sheet_rows, value_input_option="USER_ENTERED")
                progress.remove_task(page_task)
                progress.update(overall_task, advance=1)
                console.print(f"   Finished [bold]{display_name}[/], found {quotes_in_cat} new quotes.")

    except IOError as e:
        console.print(f"\n[red]File Error:[/] Could not write to file. Please check permissions or if the file is open.")
        console.print(f"   Details: {e}")
        return

    # --- Summary ---
    console.print("\n" + "=" * 50)
    if total_new_quotes > 0:
        console.print(f"Scraping complete. Added [bold]{total_new_quotes}[/] new quotes!")
    else:
        console.print("Scraping complete. No new quotes were found.")
    console.print(f"Data saved to: [bold]{out_dir}[/]")
    console.print("Done!")

if __name__ == "__main__":
    main()
