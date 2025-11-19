"""Extract a Wikipedia table.

Outputs to a JSON (default) or additionally to CSV file.

For BeautifulSoup usage, see: https://www.crummy.com/software/BeautifulSoup/bs4/doc/.

"""

import argparse
import logging
import sys
import time
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from bs4 import Tag

import scrape_tables.scrapers.scrape_wiki_table as wiki_table

# CONSTANTS
DEFAULT_URL = "https://en.wikipedia.org/wiki/List_of_James_Bond_films"
DEFAULT_TABLE = "Eon films"  # the *first* table with this caption
DEFAULT_DELAY = 0.5  # seconds between poster page requests
logger = logging.getLogger(__name__)


def parse_arguments(arg_list: list[str] | None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Extract Table from Wikipedia")

    parser.add_argument("-u", "--url", type=str, default=DEFAULT_URL, help="URL of the HTML page to get")
    parser.add_argument(
        "-t", "--table", type=str, default=DEFAULT_TABLE, help="Caption of the table to extract (case-sensitive)"
    )
    parser.add_argument(
        "--skip-posters",
        default=False,
        action="store_true",
        help="Skip following title links to fetch posters",
    )
    parser.add_argument(
        "--delay", type=float, default=DEFAULT_DELAY, help="Delay in seconds between poster page requests"
    )
    parser.add_argument("-o", "--json", type=str, default=".\\data\\table_output.json", help="Output JSON path")
    parser.add_argument("--csv", type=str, help="Output CSV path (optional)")
    parser.add_argument(
        "-v", "--verbose", action="count", default=0, help="Logging verbosity: none=WARNING, -v=INFO, -vv=DEBUG"
    )
    args: argparse.Namespace = parser.parse_args(arg_list)

    return args


def extract_infobox_poster(infobox: Tag | None) -> str | None:
    """Extract poster URL from film page infobox.

    Will only get first image.
    """
    if infobox is None:  # for type conformity
        logger.warning("Infobox is None")
        return None
    img = infobox.find("img")
    if not (img and img.has_attr("src")):
        logger.warning("No image found in infobox")
        return None
    src: str = cast("str", img["src"])  # cast for type conformity
    if src.startswith("//"):  # usually "//upload.wikimedia.org"
        return "https:" + src
    if src.startswith("/"):
        return "https://en.wikipedia.org" + src
    return src


def fetch_bond_posters(rows: list[dict[str, str]], delay: float = 0.0) -> None:
    """Fetch poster URLs by following the film page infoboxes when allowed.

    For the James Bond film specific Wikipedia pages, the poster is typically in the pages 'infobox'.
    """
    logger.info("Following title links to fetch missing posters")
    logger.debug("Sleeping for %.2f seconds between fetches", delay)
    for row in rows:
        link = row.get("_title_link")
        if not link:
            logger.warning("No title link for %s, skipping poster fetch", row.get("title"))
            logger.debug("Row: %s", row)
            continue
        film_html = wiki_table.get_html(link)  # the films page
        infobox = film_html.find("table", class_=lambda c: "infobox" in str(c))
        if not infobox:
            logger.warning("No infobox table found in %s", link)
            return
        poster = extract_infobox_poster(infobox)
        if poster:
            row["_poster_link"] = poster
            logger.debug("Fetched poster for %s from %s", row.get("title"), link)
        else:
            logger.warning("Fetch Poster failure for %s (%s)", row.get("title"), link)
            continue
        if delay and delay > 0:
            time.sleep(delay)  # avoid hammering the server


def main(arg_list: list[str] | None = None) -> None:
    """CLI entrypoint that runs the parser/extractor and writes JSON/CSV as requested."""
    # Parse Arguments and Configure Logging
    args = parse_arguments(arg_list)
    wiki_table.configure_logging(args.verbose)
    logger.debug("Passed Args: %s", ", ".join(f"{k}={v}" for k, v in vars(args).items()))

    # Generic HTML Fetch and Table Parse Functions
    soup = wiki_table.get_html(args.url)
    tbl = wiki_table.find_table_by_caption(soup, args.table)
    if not tbl:
        return  # should be able to handle this better!
    rows = wiki_table.parse_table(tbl)

    # Table Specific Functions
    if not args.skip_posters:  # pragma: no cover  # How to test this?
        fetch_bond_posters(rows, delay=args.delay)

    # Generic Save Functions
    wiki_table.save_json(rows, args.json)  # always save JSON
    if args.csv:
        wiki_table.save_csv(rows, args.csv)


if __name__ == "__main__":  # pragma: no cover  # used by pytest-cov
    print(f"Python Environment: {sys.executable}")
    main()
