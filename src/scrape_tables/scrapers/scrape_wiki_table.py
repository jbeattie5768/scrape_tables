from __future__ import annotations

import csv
import json
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

import requests
from bs4 import BeautifulSoup

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from bs4.element import Tag

# CONSTANTS
DEFAULT_URL = "https://en.wikipedia.org/wiki/List_of_James_Bond_films"
DEFAULT_TABLE_CLASS = "wikitable"  # as used by soup.find_all(table, class_=...)
DEFAULT_REQUEST_HEADERS = {"User-Agent": "wiki-table-extractor/0.1"}
DEFAULT_LOGGING_FORMAT = "%(asctime)s %(name)s %(levelname)s: %(message)s"
logger = logging.getLogger(__name__)


def request_url(url: str, headers: dict[str, str] = DEFAULT_REQUEST_HEADERS, timeout: float = 10) -> requests.Response:
    """Request the URL and return the response object."""
    logger.info("Requesting URL: %s", url)
    resp = requests.get(url, headers=headers, timeout=timeout)
    logger.debug("HTTP response: %s", resp)
    resp.raise_for_status()  # raises HTTPError for 4xx/5xx

    return resp


def get_html(url: str) -> BeautifulSoup:
    """Fetch URL and return a BeautifulSoup parsed document."""
    resp = request_url(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    return soup


def map_headers(header_tr: list[Tag] | Tag) -> dict[str, int]:  # noqa: C901 : 11>10
    """Return a mapping from table field names to column indexes.

    Accepts a single header <tr> or a sequence of header <tr>s.
    Handles colspan/rowspan by building header "chains" for each final column.
    """

    def clean_header(h: str) -> str:
        """Remove reference brackets from header text."""
        return re.sub(r"\[.*?\]", "", h).strip()

    # Normalize input to a list of rows
    header_rows: list[Tag] = [header_tr] if not isinstance(header_tr, (list, tuple)) else list(header_tr)

    headers: dict[int, list[str]] = {}  # col_index -> list of header parts (top -> bottom)
    spans_remaining: dict[int, int] = {}  # col_index -> remaining rowspan rows after current

    for row in header_rows:
        # Track rowspans introduced in this row separately so they are not
        # decremented until the next header row is processed.
        spans_to_add: dict[int, int] = {}

        # Find cells for this row
        cells = row.find_all(["th", "td"])
        col = 0
        for cell in cells:
            # skip columns already occupied by active rowspan(s)
            while spans_remaining.get(col, 0) > 0:
                col += 1

            colspan = int(str(cell.get("colspan", "1")))  # casts for type conformity
            rowspan = int(str(cell.get("rowspan", "1")))  # casts for type conformity
            text = clean_header(cell.get_text(" ", strip=True))
            # Place this header text across `colspan` columns starting at `col`
            for c in range(col, col + colspan):
                headers.setdefault(c, []).append(text)
                if rowspan > 1:
                    # Mark that this column has remaining rowspan rows after this one
                    spans_to_add[c] = spans_to_add.get(c, 0) + (rowspan - 1)
            col += colspan

        # After finishing this row, decrement remaining rowspan counters (one row consumed)
        # from previous rows, then merge in the new spans introduced on this row.
        new_spans: dict[int, int] = {}
        for c, rem in spans_remaining.items():
            decreased = rem - 1
            if decreased > 0:
                new_spans[c] = decreased
        # merge additions
        for c, add in spans_to_add.items():
            new_spans[c] = new_spans.get(c, 0) + add
        spans_remaining = new_spans

    # Convert header parts list into final header name per column
    clean_names: list[str] = []
    max_col = max(headers.keys()) if headers else -1
    for i in range(max_col + 1):
        parts = [p for p in headers.get(i, []) if p]  # filter empty parts
        name = " ".join(parts).strip()
        clean_name = clean_header(name).lower()
        clean_names.append(clean_name)

    header_map: dict[str, int] = {h: i for i, h in enumerate(clean_names) if h}
    logger.debug("Cleaned and mapped table headers: %s", header_map)

    return header_map


def extract_table_rows(tbl: Tag, hdr_map: dict[str, int]) -> list[dict[str, str]]:
    """Extract rows as dictionaries from the table and gather them together as a list.

    Drops rows that do not match header length in terms of cell count (they are likely
    header/summary rows).

    Approach: The header_map dict 'key:value' is 'names:int_index', with the value
    corresponding to the cell index (cell order) in the row:

    ┌──────┐┌──────┐┌──────┐┌──────┐┌──────┐    ┌──────┐
    │key: 0││key: 1││key: 2││key: 3││key: 4│....│key: n│
    └──────┘└──────┘└──────┘└──────┘└──────┘    └──────┘

    Each row in extracted_rows is a dict of that rows cell data, with a key corresponding to
    the hdr_map keys:

    ┌──────┐┌──────┐┌──────┐┌──────┐┌──────┐    ┌──────┐
    │Key 0 ││Key 1 ││Key 2 ││Key 3 ││Key 4 │....│Key n │
    │Cell 0││Cell 1││Cell 2││Cell 3││Cell 4│    │Cell n│
    └──────┘└──────┘└──────┘└──────┘└──────┘    └──────┘

    We take the key from the header_map and use its value to index into the row cells.
    Dicts are ordered as of Python 3.6+, so the order of keys is preserved if we wanted to
    just loop over the header_map keys, incrementally matching each to the corresponding cell.
    Instead, we loop over the header_map and use that value as the mapped row cell index
    as well as using that key for the row key.

    """
    extracted_rows: list[dict[str, str]] = []
    caption = tbl.find("caption")
    caption_text = caption.get_text().strip() if caption else ""
    if caption:
        logger.info("Extracting rows from '%s' table", caption_text)

    for tr in tbl.find_all("tr")[1:]:  # first row was header
        row_cells = tr.find_all(["th", "td"])

        # Check this row has enough cells
        if len(row_cells) < len(hdr_map):
            # Likely a header/summary row
            logger.debug("Skipping row with insufficient cells: %s", tr.get_text(" ", strip=True))
            continue

        # Map the current row's cells to hdr_keys and add the data
        map_row: dict[str, str] = {}
        for hdr_key, hdr_value in hdr_map.items():
            map_row[hdr_key] = cell_text_and_link(row_cells[hdr_value])["text"]
        # Add additional entries *not* in row or hdr_map ("" if no link)
        map_row["_title_link"] = cell_text_and_link(row_cells[hdr_map["title"]])["link"]

        logger.debug("Extracted Row: %s", map_row)
        extracted_rows.append(map_row)

    logger.debug("Extracted %d rows from '%s' table", len(extracted_rows), caption_text)

    return extracted_rows


def find_table_by_caption(
    soup: BeautifulSoup, table_caption: str, table_class: str = DEFAULT_TABLE_CLASS
) -> Tag | None:
    """Locate the specified wikitable in the parsed page.

    Approach: find a table whose caption contains the string.
    Note that this is case-sensitive matching.
    Returns the first matching table Tag, or None if table not found.

    The default 'table_class' is set to generic "wikitable". Alternatives could be:
        "wikitable sortable": more specific, but may miss some tables
        "wikitable plainrowheaders sortable": very specific
    """
    logger.info("Looking for '%s' table with caption '%s'", table_class, table_caption)
    for tbl in soup.find_all("table", class_=table_class):
        caption = tbl.find("caption")  # the tag '<caption>'
        if caption and table_caption in caption.get_text():
            logger.debug(
                "Found '%s' table with caption '%s'", " ".join(tbl.attrs["class"]), caption.get_text().strip()
            )  # remove any '\n'
            return tbl

    # Could add fallback approaches here if needed
    logger.error("Table not found (is the caption case sensitive?): %s", table_caption)

    return None  # no table found


def cell_text_and_link(cell: Tag) -> dict[str, str]:
    """Return a dict with the table cells text and a fully-qualified link (if any)."""
    text: str = cell.get_text(" ", strip=True)
    href_tag: Tag | None = cell.find("a", href=True)
    href_str = ""  # not all cells will have a link
    if href_tag:
        href = href_tag.get("href")
        if isinstance(href, str):
            href_str = "https://en.wikipedia.org" + href if href.startswith("/wiki/") else href
        else:
            href_str = str(href)  # cast for type conformity

    return {"text": text, "link": href_str}


def parse_table(tbl: Tag) -> list[dict[str, str]]:
    """Parse the table object and return cleaned rows as a list of dicts.

    This function maps headers and then extracts table rows.
    """
    first_tr: Tag | None = tbl.find("tr")
    if first_tr is None:
        logger.error("No rows found in table to parse")
        return []

    # Collect consecutive header rows starting from first_tr if they are header-only rows.
    header_rows: list[Tag] = [first_tr]
    for sibling in first_tr.find_next_siblings("tr"):
        # Treat next row as a header only if all its cells are <th>
        # This seems to be a common pattern for multi-row headers
        sibling_cells = sibling.find_all(["th", "td"])
        if not sibling_cells:
            break
        if all(c.name == "th" for c in sibling_cells):
            header_rows.append(sibling)
        else:
            break

    header_map = map_headers(header_rows if len(header_rows) > 1 else first_tr)
    table_rows = extract_table_rows(tbl, header_map)  # skips non-valid rows

    return table_rows


def save_json(data: Sequence[Mapping[str, str | int]], path: Path | str) -> None:
    """Save `data` (already-serializable) as JSON to `path`."""
    p = Path(path)

    if not p.parent.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        logger.debug("JSON folder was created: %s", p.parent)
    else:
        logger.debug("JSON folder already exists: %s", p.parent)

    with p.open("w", encoding="UTF-8") as fid:
        json.dump(data, fid, indent=2, ensure_ascii=False)
    logger.debug("Wrote %d entries to JSON file", len(data))
    logger.info("Saved JSON file: %s", p)


def save_csv(data: Sequence[Mapping[str, str | int]], path: Path | str) -> None:
    """Save `data` (already-serializable) as CSV to `path`.

    Preserves header order from 1st row.
    """
    p = Path(path)

    if not data:
        logger.warning("No data provided to save_csv; nothing written to %s", p)
        return

    if not p.parent.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        logger.debug("CSV folder was created: %s", p.parent)
    else:
        logger.debug("CSV folder already exists: %s", p.parent)

    keys = list(data[0].keys())  # preserve order, from first row
    with p.open("w", newline="", encoding="utf-8") as fid:
        writer = csv.DictWriter(fid, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)
    logger.debug("Wrote %d entries to CSV file", len(data))
    logger.info("Saved CSV file: %s", p)


def configure_logging(verbosity: int, format_string: str = DEFAULT_LOGGING_FORMAT) -> None:
    """Configure logging based on parsed arguments."""
    #                       [30               20            10]
    log_levels: list[int] = [logging.WARNING, logging.INFO, logging.DEBUG]  # verbosity: none, -v, -vv
    verbosity_level = log_levels[min(verbosity, len(log_levels) - 1)]  # cap to last level index

    root = logging.getLogger()
    root.setLevel(verbosity_level)
    if not root.handlers:
        logging.basicConfig(level=verbosity_level, format=format_string)
    else:
        for h in root.handlers:
            h.setLevel(verbosity_level)
    logger.debug("Log level set to %s", logging.getLevelName(verbosity_level))
