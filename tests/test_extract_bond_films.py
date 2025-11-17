"""Unit tests for the Bond Films table extractor.

These tests are intentionally minimal and avoid network access.
"""

import csv
import json
import logging
from pathlib import Path
from typing import Any, cast

import pytest
import responses  # A utility library for mocking out the requests Python library
from bs4 import BeautifulSoup

from src.james_bond.extract_bond_films import (
    DEFAULT_DELAY,
    extract_infobox_poster,
    fetch_bond_posters,
    main,
    parse_arguments,
)
from src.james_bond.extract_wiki_table import (
    parse_table,
)
from tests.dummy_html import (
    TEST_HTML,
    TEST_HTML_INFOBOX,
    TEST_HTML_INFOBOX_2,
    TEST_HTML_INFOBOX_3,
    TEST_HTML_INFOBOX_NO_IMG,
    TEST_HTML_INFOBOX_NO_SRC,
)

# CONSTANTS
LEN_OF_ROWS = 2  # update this if the number of rows in the test-table changes
LOGGING_LEVEL = logging.DEBUG  # For test, corresponds to -vv verbosity
VERBOSITY_LEVEL = 2  # = logging.DEBUG
STATUS_CODE_OK = 200
DEFAULT_TABLE_CLASS = "wikitable"

# Constants for test data
TEST_URL = "https://example.com/bond_films"
TEST_ROWS_DATA: list[dict[str, str | int]] = [
    {"title": "Dr. No", "year": "1962"},  # Keep year as str for CSV comparison
    {"title": "From Russia with Love", "year": "1963"},
]


@responses.activate
def test_main(tmp_path: Path) -> None:
    """Test main function with mocked requests.get()."""
    responses.get(
        TEST_URL,
        body=TEST_HTML,
        status=200,
        content_type="text/html",
    )

    json_path = tmp_path / "bond_films.json"
    csv_path = tmp_path / "bond_films.csv"
    args = [
        "--url",
        TEST_URL,
        "--table",
        "Eon films",  # Table that exists in TEST_HTML
        "--skip-posters",
        "--json",
        str(json_path),
        "--csv",
        str(csv_path),
        "-v",
    ]

    main(args)
    assert json_path.exists()
    with Path.open(json_path, "r", encoding="utf-8") as fid:
        loaded_json_data: Any = json.load(fid)
    assert loaded_json_data is not None
    assert len(cast("list[Any]", loaded_json_data)) == LEN_OF_ROWS  # cast for type conformity
    assert loaded_json_data[0]["title"] == "Dr. No"
    assert loaded_json_data[0]["year"] == "1962"
    assert loaded_json_data[1]["title"] == "From Russia with Love"
    assert loaded_json_data[1]["year"] == "1963"

    assert csv_path.exists()
    with Path.open(csv_path, "r", encoding="utf-8") as fid:
        reader = csv.DictReader(fid)
        loaded_csv_data = list(reader)
    assert len(loaded_csv_data) == LEN_OF_ROWS
    assert loaded_csv_data[0]["title"] == "Dr. No"
    assert loaded_csv_data[0]["year"] == "1962"
    assert loaded_csv_data[1]["title"] == "From Russia with Love"
    assert loaded_csv_data[1]["year"] == "1963"


@responses.activate
def test_main_missing_table(tmp_path: Path) -> None:
    """Test main function with mocked requests.get()."""
    responses.get(
        TEST_URL,
        body=TEST_HTML,
        status=200,
        content_type="text/html",
    )
    json_path = tmp_path / "bond_films.json"
    csv_path = tmp_path / "bond_films.csv"
    args = [
        "--url",
        TEST_URL,
        "--table",
        "Missing Table",  # Table that does not exist in TEST_HTML
        "--skip-posters",
        "--json",
        str(json_path),
        "--csv",
        str(csv_path),
        "-v",
    ]

    main(args)
    assert not json_path.exists()
    assert not csv_path.exists()


def test_extract_infobox_poster_no_box() -> None:
    """Test extraction of poster URL from no infobox."""
    infobox = None

    poster = extract_infobox_poster(infobox)
    assert poster is None


# URL with delimiter `//`
def test_extract_infobox_poster_double_slash() -> None:
    """Test extraction of poster URL from infobox test HTML."""
    soup = BeautifulSoup(TEST_HTML_INFOBOX, "html.parser")
    infobox = soup.find("table", {"class": "infobox vevent"})
    assert infobox is not None

    poster = extract_infobox_poster(infobox)  # code: if src.startswith("//"):
    assert poster is not None
    assert poster == "https://upload.wikimedia.org/wikipedia/en/4/43/Dr._No_-_UK_cinema_poster.jpg"


# URL with delimiter `/`
def test_extract_infobox_poster_single_slash() -> None:
    """Test extraction of poster URL from infobox test HTML."""
    soup = BeautifulSoup(TEST_HTML_INFOBOX_2, "html.parser")
    infobox = soup.find("table", {"class": "infobox vevent"})
    assert infobox is not None

    poster = extract_infobox_poster(infobox)  # code: if src.startswith("/"):
    assert poster is not None
    assert poster == "https://en.wikipedia.org/wiki/File:Dr._No_-_UK_cinema_poster.jpg"


# URL is fully qualified
def test_extract_infobox_poster_qualified() -> None:
    """Test extraction of poster URL from infobox test HTML."""
    soup = BeautifulSoup(TEST_HTML_INFOBOX_3, "html.parser")
    infobox = soup.find("table", {"class": "infobox vevent"})
    assert infobox is not None

    poster = extract_infobox_poster(infobox)  # code: return src
    assert poster is not None
    assert poster == "https://upload.wikimedia.org/wikipedia/en/a/ad/From_Russia_with_Love_-_UK_cinema_poster.jpg"


def test_extract_infobox_poster_no_image(caplog: pytest.LogCaptureFixture) -> None:
    """Test extraction of poster URL from infobox test HTML."""
    caplog.set_level(LOGGING_LEVEL)  # Debug level to capture at
    soup = BeautifulSoup(TEST_HTML_INFOBOX_NO_IMG, "html.parser")
    infobox = soup.find("table", {"class": "infobox vevent"})
    assert infobox is not None

    poster = extract_infobox_poster(infobox)
    assert poster is None
    assert "No image found in infobox" in caplog.text


def test_extract_infobox_poster_no_src(caplog: pytest.LogCaptureFixture) -> None:
    """Test extraction of poster URL from infobox testHTML."""
    caplog.set_level(LOGGING_LEVEL)  # Debug level to capture at
    soup = BeautifulSoup(TEST_HTML_INFOBOX_NO_SRC, "html.parser")
    infobox = soup.find("table", {"class": "infobox vevent"})
    assert infobox is not None

    poster = extract_infobox_poster(infobox)
    assert poster is None
    assert "No image found in infobox" in caplog.text


@pytest.mark.skip(reason="Currently need to call live network data")
def test_fetch_bond_posters() -> None:
    """Test fetching of Bond posters from test HTML.

    This is actually getting the image link from Wikipedia.
    """
    soup = BeautifulSoup(TEST_HTML, "html.parser")  # instead of get_html(URL)
    table = soup.find("table", {"class": DEFAULT_TABLE_CLASS})
    assert table is not None

    table_rows = parse_table(table)
    assert table_rows is not None

    fetch_bond_posters(table_rows, delay=1)
    # Check that each row now has a `_poster_link` key
    assert all("_poster_link" in row for row in table_rows)


def test_parse_arguments() -> None:
    """Test command-line argument parsing."""
    arg_list = [
        "--url",
        TEST_URL,
        "--table",
        "Eon films",
        "--json",
        "bond_films.json",
        "--csv",
        "bond_films.csv",
    ]
    args = parse_arguments(arg_list)

    assert args.url == TEST_URL
    assert args.json == "bond_films.json"
    assert args.csv == "bond_films.csv"
    assert args.table == "Eon films"
    assert args.skip_posters is False
    assert args.verbose == 0
    assert args.delay == DEFAULT_DELAY
