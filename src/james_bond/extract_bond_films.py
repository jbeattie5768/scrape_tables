# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "requests",
#     "beautifulsoup4",
# ]
# ///
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
import time
from pathlib import Path
from typing import TYPE_CHECKING, cast

import requests
from bs4 import BeautifulSoup, Tag

if TYPE_CHECKING:
    from bs4.element import AttributeValueList

URL = "https://en.wikipedia.org/wiki/List_of_James_Bond_films"
HEADERS = {"User-Agent": "bond-table-extractor/1.0 (https://example.com)"}

# Constants
DEFAULT_POSTER_THRESHOLD = 4
DEFAULT_DROP_EDGE_ROWS = 2
VERBOSE_DEBUG_LEVEL = 2

# configure basic logging and named logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def save_json(path: str, data: list) -> None:
    """Save `data` (already-serializable) as JSON to `path`.

    Uses pathlib to write text and logs success/failure.
    """
    json_text = json.dumps(data, indent=2, ensure_ascii=False)
    p = Path(path)
    try:
        p.write_text(json_text, encoding="utf-8")
        logger.info("Saved JSON to %s", p)
    except OSError:
        logger.exception("Failed to save JSON to %s", p)


def get_html(url: str) -> BeautifulSoup:
    """Fetch URL and return a BeautifulSoup parsed document."""
    logger.info("Fetching URL: %s", url)
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()  # raises HTTPError for 4xx/5xx
    return BeautifulSoup(resp.text, "html.parser")


def map_headers(first_tr: Tag) -> dict[str, int]:
    """Return a mapping from our target field names to column indexes."""
    headers = [th.get_text(" ", strip=True) for th in first_tr.find_all(["th", "td"])]

    def clean_header(h: str) -> str:
        return re.sub(r"\[.*?\]", "", h).strip()

    clean_headers = [clean_header(h) for h in headers]
    logger.debug("Table headers: %s", clean_headers)
    hdr_map: dict[str, int] = {}
    for i, h in enumerate(clean_headers):
        lh = h.lower()
        if re.search(r"\byear\b", lh):
            hdr_map["year"] = i
        elif "title" in lh or "film" in lh:
            hdr_map["title"] = i
        elif re.search(r"\bbond\b", lh) or "starring" in lh or "actor" in lh:
            hdr_map["bond_actor"] = i
        elif "director" in lh:
            hdr_map["director"] = i
    return hdr_map


def extract_raw_rows(tbl: Tag, hdr_map: dict[str, int]) -> list[dict[str, str]]:
    """Extract raw row dictionaries from the table (includes internal keys)."""
    raw_rows: list[dict] = []
    for tr in tbl.find_all("tr")[1:]:
        cells = tr.find_all(["th", "td"])
        if not cells:
            continue
        img = tr.find("img")
        poster_url = ""  # None
        if img and img.has_attr("src"):
            src = img["src"]
            src = cast("str", src)  # we now know it's a str
            if src.startswith("//"):
                poster_url = "https:" + src
            elif src.startswith("/"):
                poster_url = "https://en.wikipedia.org" + src
            else:
                poster_url = src

        def get_info(idx: int | None, _cells=cells) -> dict:
            if idx is None or idx >= len(_cells):
                return {"text": "", "link": None}
            return cell_text_and_link(_cells[idx])

        title_info = get_info(hdr_map.get("title"))
        title_link_internal = title_info.get("link")
        row: dict = {
            "title": title_info["text"],
            "_title_link": title_link_internal,
            "year": get_info(hdr_map.get("year"))["text"],
            "bond_actor": get_info(hdr_map.get("bond_actor"))["text"],
            "director": get_info(hdr_map.get("director"))["text"],
            "poster": poster_url or "",
        }
        raw_rows.append(row)
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


def find_eon_table(soup: BeautifulSoup) -> Tag | None:
    """Locate the Eon-Films wikitable in the parsed page.

    Approach: find a table whose caption (or preceding heading) contains 'Eon'.
    """
    # Approach: find a table whose caption (or preceding heading) contains 'Eon'
    for tbl in soup.find_all("table", class_="wikitable"):
        caption = tbl.find("caption")
        if caption and "Eon films" in caption.get_text():
            logger.info("Found Eon table by caption.")
            # logger.info("Eon table HTML: %s", tbl.prettify())
            return tbl

        # check previous significant sibling for heading text
        prev = tbl.previous_sibling
        # walk backwards skipping over strings and wrapper divs/tables
        while prev is not None:
            if isinstance(prev, Tag) and prev.name not in ("div", "table"):
                break
            # else: non-Tag (string/newline), skip it
            prev = getattr(prev, "previous_sibling", None)

        if isinstance(prev, Tag):
            # mypy/ruff: prev is Tag, so calling get_text is safe
            prev_tag: Tag = prev
            pt = prev_tag.get_text()
            if re.search(r"\bEon\b", pt, re.IGNORECASE):
                logger.info("Found Eon table by nearby heading: %s", pt.strip()[:80])
                return tbl

    # fallback: pick first wikitable with typical film headers
    for tbl in soup.find_all("table", class_="wikitable"):
        header_cells = [th.get_text(strip=True) for th in tbl.find_all("th")]
        if any(h.lower() in ("title", "film", "year") for h in header_cells):
            logger.info("Using fallback wikitable (headers include title/year).")
            return tbl
    return None


def cell_text_and_link(cell: Tag) -> dict[str, str | AttributeValueList | None]:
    """Return a dict with visible text and a fully-qualified first link (if any)."""
    text: str = cell.get_text(" ", strip=True)
    a: Tag | None = cell.find("a", href=True)
    href: str | AttributeValueList | None = None
    if a:
        href = a.get("href")
        if isinstance(href, str) and href.startswith("/wiki/"):
            href = "https://en.wikipedia.org" + href

    return {"text": text, "link": href}


def parse_table(
    tbl: Tag, poster_threshold: int = DEFAULT_POSTER_THRESHOLD, *, skip_posters: bool = False, delay: float = 0.0
) -> list[dict[str, str]]:
    """Parse the Eon films table and return cleaned rows.

    This function maps headers, extracts raw rows, optionally follows title
    links to fetch missing poster images (controlled by poster_threshold),
    and drops obvious header/summary rows before returning a list of dicts.
    """
    first_tr: Tag | None = tbl.find("tr")
    first_tr = cast("Tag", first_tr)  # we now know it's a Tag
    hdr_map = map_headers(first_tr)
    logger.info("Table headers mapping: %s", hdr_map)
    raw_rows = extract_raw_rows(tbl, hdr_map)
    logger.info("Collected %d raw rows from table (including possible header/summary rows)", len(raw_rows))

    if not skip_posters:
        fetch_posters(raw_rows, poster_threshold, delay=delay)
    else:
        logger.info("Skipping poster fetching as requested")

    results = raw_rows
    if len(results) > DEFAULT_DROP_EDGE_ROWS:
        logger.info("Dropping first and last rows (assumed header/summary)")
        results = results[1:-1]

    # strip internal-only keys (like _title_link) before returning
    for r in results:
        r.pop("_title_link", None)
        if "poster" not in r:
            r["poster"] = ""

    logger.info("Returning %d parsed film rows", len(results))
    return results


def write_csv(rows: list[dict[str, str]], path: str) -> None:
    """Write rows to CSV (preserving key order discovered in rows)."""
    if not rows:
        logger.info("No rows to write to CSV.")
        return
    keys: list[str] = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    p = Path(path)
    with p.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def main():
    """CLI entrypoint that runs the extractor and writes JSON/CSV as requested."""
    parser = argparse.ArgumentParser(description="Extract James Bond Films Table from Wikipedia")
    parser.add_argument(
        "-v", "--verbose", action="count", default=0, help="Logging verbosity: none=WARNING, -v=INFO, -vv=DEBUG"
    )
    parser.add_argument("--threshold", type=int, default=4, help="Maximum missing posters to follow links")
    parser.add_argument("--skip-posters", action="store_true", help="Skip following title links to fetch posters")
    parser.add_argument("--delay", type=float, default=0.0, help="Delay in seconds between poster page requests")
    parser.add_argument("-o", "--output", default=r".\\data\\james_bond_films.json", help="Output JSON path")
    parser.add_argument("--csv", help="Optional CSV output path")
    args = parser.parse_args()

    # adjust logging level
    if args.verbose >= VERBOSE_DEBUG_LEVEL:
        level = logging.DEBUG
    elif args.verbose == 1:
        level = logging.INFO
    else:
        level = logging.WARNING
    logging.getLogger().setLevel(level)

    soup_obj = get_html(URL)
    tbl = find_eon_table(soup_obj)
    if not tbl:
        logger.error("Eon films table not found.")
        return
    rows = parse_table(tbl, poster_threshold=args.threshold, skip_posters=args.skip_posters, delay=args.delay)
    # print JSON to stdout at INFO level (or DEBUG for more)
    logger.info("Parsed %d rows; writing JSON to %s", len(rows), args.output)
    save_json(args.output, rows)
    if args.csv:
        write_csv(rows, args.csv)


if __name__ == "__main__":
    main()
