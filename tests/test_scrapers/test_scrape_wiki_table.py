"""Unit tests for the Wiki table scraper.

These tests avoid network access, whether through mocking or the responses library.
"""

import csv
import json
import logging
from pathlib import Path
from typing import cast

import pytest
import requests
import responses  # A utility library for mocking out the requests Python library
from bs4 import BeautifulSoup, Tag

# Import as package name from src layout
from scrape_tables.scrapers.scrape_wiki_table import (
    cell_text_and_link,
    configure_logging,
    extract_table_rows,
    find_table_by_caption,
    get_html,
    map_headers,
    parse_table,
    request_url,
    save_csv,
    save_json,
)
from tests.fixtures import (
    TEST_HTML,
    TEST_HTML_INFOBOX,
    TEST_HTML_NO_ROWS,
    TEST_HTML_SHORT_ROW,
)

# CONSTANTS
LEN_OF_ROWS = 2  # update this if the number of rows in the test-table changes
# LOGGING_LEVEL = logging.DEBUG  # For test, corresponds to -vv verbosity
VERBOSITY_LEVEL = 2  # = logging.DEBUG
STATUS_CODE_OK = 200
DEFAULT_TABLE_CLASS = "wikitable"

# Constants for test data
TEST_URL = "https://example.com/bond_films"
TEST_ROWS_DATA: list[dict[str, str | int]] = [
    {"title": "Dr. No", "year": "1962"},  # Keep year as str for CSV comparison
    {"title": "From Russia with Love", "year": "1963"},
]


def test_map_headers() -> None:
    """Test mapping of table headers to expected keys."""
    expected_map = {"title": 0, "year": 1, "bond actor": 2, "director": 3}
    soup = BeautifulSoup(TEST_HTML, "html.parser")
    tbl = find_table_by_caption(soup, "Eon films")
    assert tbl is not None

    first_tr = tbl.find("tr")
    assert first_tr is not None

    header_map = map_headers(first_tr)
    assert header_map == expected_map


def test_extract_table_rows() -> None:
    """Test extraction of table rows."""
    soup = BeautifulSoup(TEST_HTML, "html.parser")
    tbl = find_table_by_caption(soup, "Eon films")
    assert tbl is not None

    first_tr = tbl.find("tr")
    header_map = map_headers(cast("Tag", first_tr))  # cast for type conformity
    assert header_map is not None

    table_rows = extract_table_rows(tbl, header_map)
    assert len(table_rows) == LEN_OF_ROWS
    first_row = table_rows[0]
    assert first_row["title"] == "Dr. No"
    assert first_row["year"] == "1962"
    assert first_row["bond actor"] == "Sean Connery"
    assert first_row["director"] == "Terence Young"


def test_extract_table_rows_short_row(caplog: pytest.LogCaptureFixture) -> None:
    """Test extraction of table rows with short rows."""
    caplog.set_level(logging.DEBUG)
    soup = BeautifulSoup(TEST_HTML_SHORT_ROW, "html.parser")
    tbl = find_table_by_caption(soup, "Eon films")
    assert tbl is not None

    first_tr = tbl.find("tr")
    header_map = map_headers(cast("Tag", first_tr))  # cast for type conformity
    assert header_map is not None

    table_rows = extract_table_rows(tbl, header_map)
    # There should have been short-rows detected and ignored
    assert len(table_rows) == 0
    assert "Skipping row with insufficient cells: Dr. No 1962" in caplog.text
    assert "Skipping row with insufficient cells: From Russia with Love 1963" in caplog.text


def test_cell_text_and_link() -> None:
    """Test extraction of text and link from a table cell."""
    soup = BeautifulSoup(TEST_HTML, "html.parser")
    tbl = find_table_by_caption(soup, "Eon films")
    assert tbl is not None

    first_row = tbl.find_all("tr")[1]  # skip header row
    row_cells = first_row.find_all(["th", "td"])
    assert row_cells is not None

    # Extract text and link from the first cell
    title_cell = cell_text_and_link(row_cells[0])["text"]
    link_cell = cell_text_and_link(row_cells[0])["link"]
    assert title_cell == "Dr. No"
    assert link_cell == "https://en.wikipedia.org/wiki/Dr._No_(film)"


def test_cell_text_and_link_non_string_href() -> None:
    """When an anchor has a no string-href (e.g. list), ensure test code falls back to it having been stringified."""
    soup = BeautifulSoup("<td><a>Title</a></td>", "html.parser")  # no href
    tag_a = soup.find("a")
    assert tag_a is not None

    # Simulate a multi-valued attribute for the test
    tag_a["href"] = ["/wiki/A", "/wiki/B"]  # type: ignore[assignment]
    cell = soup.find("td")
    assert cell is not None
    title_cell = cell_text_and_link(cell)["text"]
    link_cell = cell_text_and_link(cell)["link"]
    assert title_cell == "Title"
    assert "/wiki/A" in link_cell  # should be stringified


def test_configure_logging(caplog: pytest.LogCaptureFixture) -> None:
    """Test logging configuration based on verbosity level.

    Check the logging output via the caplog fixture.
    """
    caplog.set_level(logging.DEBUG)
    configure_logging(VERBOSITY_LEVEL)
    assert f"Log level set to {logging.getLevelName(logging.DEBUG)}" in caplog.text


def test_configure_logging_no_root_handlers(caplog: pytest.LogCaptureFixture) -> None:
    """When the root logger has no handlers, `configure_logging` should call basicConfig and log the level."""
    root = logging.getLogger()
    # Save and remove existing handlers to simulate 'no handlers' path
    saved_handlers = list(root.handlers)
    for h in saved_handlers:
        root.removeHandler(h)
    try:
        caplog.set_level(logging.DEBUG)
        configure_logging(VERBOSITY_LEVEL)

        assert root.handlers, "basicConfig did not add a handler to root"
        assert root.level == logging.DEBUG
    finally:
        # restore original handlers
        for h in list(root.handlers):
            root.removeHandler(h)
        for h in saved_handlers:
            root.addHandler(h)


def test_save_json_exist_folder(tmp_path: Path) -> None:
    """Test saving JSON data to a file.

    This test uses an existing folder.
    """
    file_path = tmp_path / "bond_films.json"

    save_json(TEST_ROWS_DATA, file_path)
    assert file_path.exists()
    with Path.open(file_path, "r", encoding="utf-8") as f:
        loaded_data = json.load(f)
    assert loaded_data == TEST_ROWS_DATA


def test_save_json_new_folder(caplog: pytest.LogCaptureFixture, tmp_path: Path) -> None:
    """Test saving JSON data to a file.

    This test creates a new folder.
    """
    file_path = tmp_path / "jbf/bond_films.json"  # jbf is the new folder
    caplog.set_level(logging.DEBUG)

    save_json(TEST_ROWS_DATA, file_path)
    assert file_path.exists()
    with Path.open(file_path, "r", encoding="utf-8") as f:
        loaded_data = json.load(f)
    assert loaded_data == TEST_ROWS_DATA
    assert "JSON folder was created: " in caplog.text


def test_save_csv(tmp_path: Path) -> None:
    """Test saving CSV data to a file.

    This test uses an existing folder.
    """
    file_path = tmp_path / "bond_films.csv"

    save_csv(TEST_ROWS_DATA, file_path)
    assert file_path.exists()
    with Path.open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        loaded_data = list(reader)
    assert loaded_data == TEST_ROWS_DATA


def test_save_csv_new_folder(caplog: pytest.LogCaptureFixture, tmp_path: Path) -> None:
    """Test saving CSV data to a file.

    This test creates a new folder.
    """
    file_path = tmp_path / "jbf/bond_films.csv"  # jbf is the new folder
    caplog.set_level(logging.DEBUG)  # captures lower as well, e.g. INFO

    save_csv(TEST_ROWS_DATA, file_path)
    assert file_path.exists()
    assert "CSV folder was created: " in caplog.text
    with Path.open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        loaded_data = list(reader)
    assert loaded_data == TEST_ROWS_DATA
    assert "Saved CSV file" in caplog.text


def test_save_csv_no_data(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """save_csv should do nothing and log a warning when passed empty data."""
    file_path = tmp_path / "no_data.csv"
    caplog.set_level(logging.WARNING)

    save_csv([], file_path)  # empty data
    assert not file_path.exists()
    assert "No data provided to save_csv" in caplog.text


def test_parse_table() -> None:
    """Test parsing a table."""
    soup = BeautifulSoup(TEST_HTML, "html.parser")
    tbl = find_table_by_caption(soup, "Eon films")
    assert tbl is not None

    rows = parse_table(tbl)
    assert len(rows) == LEN_OF_ROWS
    first = rows[0]
    assert first["title"] == "Dr. No"
    assert first["year"] == "1962"
    assert first["bond actor"] == "Sean Connery"
    assert first["director"] == "Terence Young"


def test_parse_table_no_rows() -> None:
    """parse_table should return empty list when table has no rows."""
    soup = BeautifulSoup(TEST_HTML_NO_ROWS, "html.parser")
    tbl = soup.find("table")
    assert tbl is not None
    rows = parse_table(tbl)
    assert rows == []


def test_find_table_by_caption() -> None:
    """Test finding a table by its caption."""
    soup = BeautifulSoup(TEST_HTML, "html.parser")
    assert soup is not None

    table = find_table_by_caption(soup, table_caption="Eon films", table_class=DEFAULT_TABLE_CLASS)
    assert table is not None
    assert table.name == "table"

    caption = table.find("caption")
    assert caption is not None
    assert caption.text.strip() == "Eon films"


def test_find_table_by_caption_no_table() -> None:
    """Try to find a non-existent table by its caption."""
    soup = BeautifulSoup(TEST_HTML_INFOBOX, "html.parser")
    assert soup is not None

    table = find_table_by_caption(soup, table_caption="Eon films", table_class=DEFAULT_TABLE_CLASS)
    assert table is None


@responses.activate
def test_request_url_ok() -> None:
    """Test requesting a URL.

    This uses the responses library to mock the requests.get() functionality.
    """
    responses.get(
        TEST_URL,
        body=TEST_HTML,
        status=STATUS_CODE_OK,
        content_type="text/html",
    )

    resp = request_url(TEST_URL)
    assert resp.status_code == STATUS_CODE_OK

    # Confirm it is valid data
    soup = BeautifulSoup(resp.text, "html.parser")
    assert soup is not None
    title = soup.find("title")
    assert title is not None
    assert title.text == "James Bond Films"  # From MOCK_HTML


@responses.activate
def test_request_url_error() -> None:
    """Test when requesting a URL returns an error.

    This uses the responses library to mock the requests.get() functionality.
    """
    responses.get(
        TEST_URL,
        body=TEST_HTML,
        status=401,
        content_type="text/html",
    )

    with pytest.raises(requests.exceptions.HTTPError) as err_msg:
        request_url(TEST_URL, timeout=10)
    print(err_msg)
    assert "401" in str(err_msg.value)


@responses.activate
def test_get_html() -> None:
    """Fetch URL and return a BeautifulSoup parsed document.

    This uses the responses library to mock the requests.get() functionality.
    """
    responses.get(
        TEST_URL,
        body=TEST_HTML,
        status=200,
        content_type="text/html",
    )

    soup = get_html(TEST_URL)
    assert soup is not None

    # Confirm it is valid data
    title = soup.find("title")
    assert title is not None
    assert title.text == "James Bond Films"
