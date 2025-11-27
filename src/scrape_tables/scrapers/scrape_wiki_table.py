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


def map_headers(header_tr: list[Tag] | Tag) -> dict[str, int]:
    """Return a mapping from table field names to column indexes.

    Accepts a single header <tr> or a sequence of header <tr>'s.
    """
    # Normalize input to a list of rows: row arg is either a single Tag or a list of Tags
    header_rows: list[Tag] = [header_tr] if not isinstance(header_tr, (list, tuple)) else list(header_tr)

    headers, _ = parse_header_rows(header_rows)  # handles colspan/rowspan
    clean_names = build_clean_names(headers)
    # Map the cleaned names to the headers original column indexes: {"name": index}
    header_map: dict[str, int] = {header: idx for idx, header in enumerate(clean_names) if header}
    logger.debug("Cleaned and mapped table headers: %s", header_map)

    return header_map


def build_clean_names(headers: dict[int, list[str]]) -> list[str]:
    """Build final header names from header parts and cleanup the name.

    Header parts are lists of strings for each column, e.g.::

    headers: {0: ['Header1'], 1: ['Header2'], 2: ['Header3', 'Header3.1', 'Header3.2']}

    Where there is more than one part (index 2 in the example), they are joined with a space.
    All header names are converted to lowercase.
    """
    clean_names: list[str] = []

    for value in headers.values():
        name = " ".join([x.strip() for x in value])  # strip each string in list and join
        cleaned = clean_cell(name).lower()
        clean_names.append(cleaned)

    logger.debug("Built clean header names: %s", clean_names)

    return clean_names


def parse_header_rows(header_rows: list[Tag]) -> tuple[dict[int, list[str]], dict[int, int]]:
    """Parse header rows and return headers and spans_remaining.

    This handles header rows that include rowspan/colspan tags.
    Approach:
    When we encounter a cell with a rowspan, we add it to the
    'spans_remaining' dict to track how many more rows it will occupy.
    The dict maps column indexes to the number of remaining rows that
    the rowspan covers, e.g. if a cell at column 2 has a rowspan of 3,
    spans_remaining[2] would be 3::

    spans_remaining: {0: 1, 1: 1, 2: 3}

    As we process each header row, we skip columns that are occupied by active
    rowspans. For active rowspans we append that new row-part to the existing
    header. This means we can end up with a list of header parts for each column.
    These parts are stored in the 'headers' dict, e.g.::

    headers: {0: ['Header1'], 1: ['Header2'], 2: ['Header3', 'Header3.1', 'Header3.2']}

    We return this dict, other functions handle the cleaning and joining of these parts,
    """
    headers: dict[int, list[str]] = {}  # {col_index: list of header parts (top -> bottom)}
    spans_remaining: dict[int, int] = {}  # {col_index: remaining rowspan rows after current}

    for row in header_rows:
        # Track rowspans in this row separately so they are not
        # decremented until the next header row is processed
        rowspans_to_add: dict[int, int] = {}

        # Find cells for this row
        cells = row.find_all(["th", "td"])
        col_index = 0  # Keep a tally of current column index
        for cell in cells:
            # skip columns already occupied by active rowspan(s)
            while spans_remaining.get(col_index, 0) > 0:
                col_index += 1

            # If there is a colspan/rowspan, get how many it spans, otherwise its just 1 col/row
            colspan = int(str(cell.get("colspan", "1")))  # casts for type conformity
            rowspan = int(str(cell.get("rowspan", "1")))  # casts for type conformity
            # Clean the cell. Use strip as multi-row will likely have '\n' at the end of the string
            text = clean_cell(cell.get_text(" ", strip=True))

            # Place this cell text across `colspan` columns starting at `col`
            for c in range(col_index, col_index + colspan):
                headers.setdefault(c, []).append(text)
                if rowspan > 1:  # mark that this col has remaining rowspan rows after this one
                    rowspans_to_add[c] = rowspans_to_add.get(c, 0) + (rowspan - 1)
            col_index += colspan

        # After finishing this row, decrement remaining rowspan counters (one row consumed),
        # then merge in the new spans introduced on this row
        new_spans: dict[int, int] = {}
        for c, remaining in spans_remaining.items():
            decreased = remaining - 1
            if decreased > 0:
                new_spans[c] = decreased

        for c, add in rowspans_to_add.items():  # merge additions
            new_spans[c] = new_spans.get(c, 0) + add

        spans_remaining = new_spans  # we do nothing with this, for future use

    logger.debug("Final spans remaining after header parsing: %s", spans_remaining)
    logger.debug("Parsed header rows: %s", headers)

    return headers, spans_remaining


def clean_cell(h: str) -> str:
    """Remove unwanted text from header text.

    This includes:
        * Reference Brackets, e.g. '[12]'
        * Leading/trailing whitespace
    """
    removed_refs = re.sub(r"\[.*?\]", "", h).strip()
    stripped_ws = removed_refs.strip()  # likely already done, but just in case

    return stripped_ws


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
    text: str = clean_cell(cell.get_text(" ", strip=True))  # get and clean cell contents
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

    This function maps headers and extracts table rows.
    """
    first_tr: Tag | None = tbl.find("tr")  # expected to be header row
    if first_tr is None:
        logger.error("No rows found in table to parse")
        return []

    header_rows: list[Tag] = [first_tr]
    # Some header rows may have sub-rows via colspan/rowspan tags
    # Treat sub-rows as a header only if *all* their cells are <th>
    # This seems to be a common pattern for multi-row headers
    for sibling in first_tr.find_next_siblings("tr"):
        sibling_cells = sibling.find_all(["th", "td"])
        if not sibling_cells:
            break
        if all(c.name == "th" for c in sibling_cells):
            header_rows.append(sibling)
        else:
            break

    header_map = map_headers(header_rows)
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
