import csv
import json
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, cast

import requests
from bs4 import BeautifulSoup

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from bs4 import Tag
    from bs4.element import AttributeValueList

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


def map_headers(first_tr: Tag) -> dict[str, int]:
    """Return a mapping from table field names to column indexes."""

    def clean_header(h: str) -> str:
        """Remove reference brackets from header text."""
        return re.sub(r"\[.*?\]", "", h).strip()

    headers = [th.get_text(" ", strip=True) for th in first_tr.find_all(["th", "td"])]
    clean_headers = [clean_header(h) for h in headers]
    header_map: dict[str, int] = {h.lower(): i for i, h in enumerate(clean_headers)}
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
    if caption:  # for type conformity
        logger.info("Extracting rows from '%s' table", caption.get_text().strip())

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

    logger.debug("Extracted %d rows from '%s' table", len(extracted_rows), caption)

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
    href: str | AttributeValueList | None = ""  # not all cells will have a link
    if href_tag:
        href = href_tag.get("href")
        if isinstance(href, str) and href.startswith("/wiki/"):
            href = "https://en.wikipedia.org" + href

    return {"text": text, "link": str(href)}  # cast for type conformity


def parse_table(tbl: Tag) -> list[dict[str, str]]:
    """Parse the table object and return cleaned rows as a list of dicts.

    This function maps headers, extracts table rows.
    """
    first_tr: Tag | None = tbl.find("tr")
    first_tr = cast("Tag", first_tr)  # cast for type conformity
    header_map = map_headers(first_tr)
    table_rows = extract_table_rows(tbl, header_map)  # skips non-valid rows

    return table_rows


def save_json(data: Sequence[Mapping[str, str | int]], path: Path | str) -> None:
    """Save `data` (already-serializable) as JSON to `path`."""
    p = Path(path)
    try:
        p.parents[0].mkdir(parents=True)
    except FileExistsError:
        logger.debug("JSON folder already exists: %s", p.parents[0])
    else:
        logger.debug("JSON folder was created: %s", p.parents[0])

    with p.open("w", encoding="UTF-8") as fid:
        json.dump(data, fid, indent=2, ensure_ascii=False)
    logger.debug("Wrote %d entries to JSON file", len(data))
    logger.info("Saved JSON file: %s", p)


def save_csv(data: Sequence[Mapping[str, str | int]], path: Path | str) -> None:
    """Save `data` (already-serializable) as CSV to `path`.

    Preserves header order from 1st row.
    """
    p = Path(path)
    try:
        p.parents[0].mkdir(parents=True)
    except FileExistsError:
        logger.debug("CSV folder already exists: %s", p.parents[0])
    else:
        logger.debug("CSV folder was created: %s", p.parents[0])

    keys = data[0].keys()  # preserve order, from first row
    with p.open("w", newline="", encoding="utf-8") as fid:
        writer = csv.DictWriter(fid, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)
    logger.debug("Wrote %d entries to CSV file", len(data))
    logger.info("Saved CSV  file: %s", p)


def configure_logging(verbosity: int, format_string: str = DEFAULT_LOGGING_FORMAT) -> None:
    """Configure logging based on parsed arguments."""
    #                       [30               20            10]
    log_levels: list[int] = [logging.WARNING, logging.INFO, logging.DEBUG]  # verbosity: none, -v, -vv
    verbosity_level = log_levels[min(verbosity, len(log_levels) - 1)]  # cap to last level index
    logging.basicConfig(level=verbosity_level, format=format_string)
    logger.debug("Log level set to %s", logging.getLevelName(verbosity_level))
