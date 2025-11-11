"""Extract the Eon films table.

Extract the "Eon films" table from:
https://en.wikipedia.org/wiki/List_of_James_Bond_films

Outputs JSON to stdout and can optionally write CSV.
Requires: requests, beautifulsoup4
"""

import argparse
import csv
import json
import logging
import re
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, cast

import requests
from bs4 import BeautifulSoup, Tag

if TYPE_CHECKING:
    from bs4.element import AttributeValueList

REQ_HEADERS = {"User-Agent": "wiki-table-extractor/0.1"}
DEFAULT_URL = "https://en.wikipedia.org/wiki/List_of_James_Bond_films"
DEFAULT_LOGGING_LEVEL = logging.INFO
DEFAULT_POSTER_THRESHOLD = 4  # TODO@jb: #007 review if this is appropriate

logging.basicConfig(level=DEFAULT_LOGGING_LEVEL, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)
log_levels = [logging.WARNING, logging.INFO, logging.DEBUG]  # verbosity: None, -v, -vv


def _parse_arguments(arg_list: list[str] | None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Extract Table from Wikipedia")

    # All Optional: defaults for some
    parser.add_argument("-u", "--url", type=str, default=DEFAULT_URL, help="URL of the Wikipedia page to extract")
    parser.add_argument("-t", "--table", type=str, help="Name of the table to extract (case-sensitive)", required=True)
    parser.add_argument("--threshold", type=int, default=4, help="Maximum missing posters to follow links")
    parser.add_argument("--skip-posters", action="store_true", help="Skip following title links to fetch posters")
    parser.add_argument("--delay", type=float, default=0.0, help="Delay in seconds between poster page requests")
    parser.add_argument("-o", "--output", default=r".\\data\\table_output.json", help="Output JSON path")
    parser.add_argument("--csv", type=str, help="Optional CSV output path")
    parser.add_argument(
        "-v", "--verbose", action="count", default=0, help="Logging verbosity: none=WARNING, -v=INFO, -vv=DEBUG"
    )
    args = parser.parse_args(arg_list)
    # Set to log at DEFAULT_LOGGING_LEVEL as logging level not yet set
    logger.log(DEFAULT_LOGGING_LEVEL, "Passed Args: %s", ", ".join(f"{k}={v}" for k, v in vars(args).items()))

    return args


def save_json(data: list[dict[str, str]], path: str) -> None:
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
    logger.info("Wrote %d entries to JSON file: %s", len(data), p)


def get_html(url: str) -> BeautifulSoup:
    """Fetch URL and return a BeautifulSoup parsed document."""
    logger.info("Fetching URL: %s", url)
    resp = requests.get(url, headers=REQ_HEADERS, timeout=15)
    logger.debug("HTTP response: %s", resp)
    resp.raise_for_status()  # raises HTTPError for 4xx/5xx

    return BeautifulSoup(resp.text, "html.parser")


def map_headers(first_tr: Tag) -> dict[str, int]:
    """Return a mapping from our target field names to column indexes."""

    def clean_header(h: str) -> str:
        """Remove reference brackets from header text."""
        return re.sub(r"\[.*?\]", "", h).strip()

    headers = [th.get_text(" ", strip=True) for th in first_tr.find_all(["th", "td"])]
    clean_headers = [clean_header(h) for h in headers]
    header_map: dict[str, int] = {h.lower(): i for i, h in enumerate(clean_headers)}
    logger.debug("Cleaned and mapped table headers: %s", header_map)

    return header_map


def extract_raw_rows(tbl: Tag, hdr_map: dict[str, int]) -> list[dict[str, str]]:
    """Extract rows as dictionaries from the table.

    Drops rows that do not match header length in terms of cell count (they are likely header/summary
    rows), before returning a list of row dicts.
    """
    raw_rows: list[dict[str, str]] = []

    for tr in tbl.find_all("tr")[1:]:  # first was header
        cells = tr.find_all(["th", "td"])
        if not cells:
            continue
        # img = tr.find("img")
        # poster_url = ""  # None
        # if img and img.has_attr("src"):
        #     src = img["src"]
        #     src = cast("str", src)  # we now know it's a str
        #     if src.startswith("//"):
        #         poster_url = "https:" + src
        #     elif src.startswith("/"):
        #         poster_url = "https://en.wikipedia.org" + src
        #     else:
        #         poster_url = src

        # def get_info(idx: int | None, _cells=cells) -> dict:
        #     if idx is None or idx >= len(_cells):
        #         return {"text": "", "link": None}
        #     return cell_text_and_link(_cells[idx])

        # title_info = get_info(hdr_map.get("title"))
        # title_link_internal = title_info.get("link")
        # row: dict = {
        #     "title": title_info["text"],
        #     "_title_link": title_link_internal,
        #     "year": get_info(hdr_map.get("year"))["text"],
        #     "bond_actor": get_info(hdr_map.get("bond_actor"))["text"],
        #     "director": get_info(hdr_map.get("director"))["text"],
        #     # "poster": poster_url or "",
        # }

        # Check this is a valid row, i.e. has enough cells
        # Even a row with blank entries will have the same number of cells
        if len(cells) < len(hdr_map):
            logger.warning("Skipping row with insufficient cells: %s", tr.get_text(" ", strip=True))
            continue

        row: dict[str, str] = {}
        for idx, hdr_key in enumerate(hdr_map):
            row[hdr_key] = cell_text_and_link(cells[idx])["text"]  # extract text only
        logger.debug("Extracted Row = %s", row)
        raw_rows.append(row)

    logger.info("Collected %d raw rows from table (including possible header/summary rows)", len(raw_rows))

    return raw_rows


def _extract_infobox_poster(infobox: Tag | None) -> str | None:
    if not infobox:
        return None
    img = infobox.find("img")
    if not (img and img.has_attr("src")):
        return None
    src = img["src"]
    src = cast("str", src)  # we now know it's a str
    if src.startswith("//"):
        return "https:" + src
    if src.startswith("/"):
        return "https://en.wikipedia.org" + src
    return src


def fetch_posters(rows: list[dict[str, str]], poster_threshold: int, delay: float = 0.0) -> None:
    """Fill missing poster URLs by following the film page infoboxes when allowed."""
    missing = [r for r in rows if not r.get("poster")]
    logger.info("Rows missing poster: %d", len(missing))
    try:
        pt = int(poster_threshold)
    except (TypeError, ValueError):
        pt = DEFAULT_POSTER_THRESHOLD
    follow_links = len(missing) > 0 and (pt <= 0 or len(missing) <= pt)
    if not follow_links:
        logger.info("Not following title links to fetch posters (threshold=%s)", pt)
        return

    logger.info("Following title links to fetch missing posters (missing=%d)", len(missing))
    for r in missing:
        link = r.get("_title_link")
        if not link:
            logger.debug("No title link for %s, skipping poster fetch", r.get("title"))
            continue
        try:
            film_html = get_html(link)
            # infobox = film_html.find("table", class_=lambda c: c and "infobox" in c)
            infobox = film_html.find("table", class_=lambda c: "infobox" in str(c))
            poster = _extract_infobox_poster(infobox)
            if poster:
                r["poster"] = poster
                logger.info("Fetched poster for %s from %s", r.get("title"), link)
            else:
                logger.warning("No poster image found in infobox for %s", r.get("title"))
        except requests.RequestException:
            logger.exception("Network error fetching poster for %s (%s)", r.get("title"), link)
        if delay and delay > 0:
            time.sleep(delay)


def find_table_by_caption(soup: BeautifulSoup, table_caption: str) -> Tag | None:
    """Locate the specified wikitable in the parsed page.

    Approach: find a table whose caption contains the string.
    Note that this is case-sensitive matching.
    Returns the first matching table Tag, or None if string not found.
    """
    for tbl in soup.find_all("table", class_="wikitable"):
        caption = tbl.find("caption")  # Find the tag <caption>
        if caption and table_caption in caption.get_text():
            logger.info("Found table by caption: %s", caption.get_text().strip())  # remove stray '\n'
            return tbl

    # Could add fallback approaches here if needed
    logger.error("Table not found (is it case sensitive?): %s", table_caption)

    return None  # No table found


def cell_text_and_link(cell: Tag) -> dict[str, str]:
    """Return a dict with text and a fully-qualified link (if any)."""
    text: str = cell.get_text(" ", strip=True)
    href_tag: Tag | None = cell.find("a", href=True)
    href: str | AttributeValueList | None = ""
    if href_tag:
        href = href_tag.get("href")
        if isinstance(href, str) and href.startswith("/wiki/"):
            href = "https://en.wikipedia.org" + href

    return {"text": text, "link": str(href)}  # cast to str for type consistency


def parse_table(
    tbl: Tag, poster_threshold: int = DEFAULT_POSTER_THRESHOLD, *, skip_posters: bool = False, delay: float = 0.0
) -> list[dict[str, str]]:
    """Parse the table and return cleaned rows.

    This function maps headers, extracts raw rows.
    Optionally follows title links to fetch poster images.

    """
    first_tr: Tag | None = tbl.find("tr")
    first_tr = cast("Tag", first_tr)  # Keep type-check happy, we now know it's a Tag
    header_map = map_headers(first_tr)
    raw_rows = extract_raw_rows(tbl, header_map)  # Drops any non-conforming rows

    if not skip_posters:
        fetch_posters(raw_rows, poster_threshold, delay=delay)
    else:
        logger.info("Skipping poster fetching as requested")

    logger.info("Returning %d parsed film rows", len(raw_rows))

    return raw_rows


def save_csv(rows: list[dict[str, str]], path: str) -> None:
    """Write rows to CSV (preserving key order from 1st row)."""
    p = Path(path)
    try:
        p.parents[0].mkdir(parents=True)
    except FileExistsError:
        logger.debug("CSV folder already exists: %s", p.parents[0])
    else:
        logger.debug("CSV folder was created: %s", p.parents[0])

    keys = rows[0].keys()  # preserve order from first row
    with p.open("w", newline="", encoding="utf-8") as fid:
        writer = csv.DictWriter(fid, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)
    logger.info("Wrote %d rows to CSV file: %s", len(rows), p)


def set_log_level(verbose: int) -> None:
    """Adjust logging level based on verbosity level."""
    # 'WARNING': 30, 'INFO': 20, 'DEBUG': 10
    level = log_levels[min(verbose, len(log_levels) - 1)]  # cap to last level index
    logger.debug("Setting log level to %s", logging.getLevelName(level))
    logging.getLogger().setLevel(level)


def main(arg_list: list[str] | None = None) -> None:
    """CLI entrypoint that runs the extractor and writes JSON/CSV as requested."""
    args = _parse_arguments(arg_list)
    set_log_level(args.verbose)

    soup = get_html(args.url)
    tbl = find_table_by_caption(soup, args.table)
    if not tbl:
        return  # We should be able to handle this better
    rows = parse_table(tbl, poster_threshold=args.threshold, skip_posters=args.skip_posters, delay=args.delay)
    save_json(rows, args.output)
    if args.csv:
        save_csv(rows, args.csv)


if __name__ == "__main__":
    print(f"Python Environment: {sys.executable}")
    main()
