"""Unit tests for the Bond table extractor.

These tests are intentionally minimal and avoid network access.
"""

import csv
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from unittest import mock

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

import pytest
import requests
from bs4 import BeautifulSoup, Tag

from src.james_bond.extract_bond_films import (
    DEFAULT_TABLE_CLASS,
    cell_text_and_link,
    configure_logging,
    extract_infobox_poster,
    extract_table_rows,
    fetch_bond_posters,
    find_table_by_caption,
    get_html,
    main,
    map_headers,
    parse_arguments,
    parse_table,
    request_url,
    save_csv,
    save_json,
)

LEN_OF_ROWS = 2  # update this if the number of rows in the test-table changes
LOGGING_LEVEL = logging.DEBUG  # For test, corresponds to -vv verbosity
STATUS_CODE_OK = 200

# Constants for test data
TEST_URL = "https://example.com"
MOCK_HTML = """
    <html>
        <head><title>James Bond Films</title></head>
            <body>
                <table class="wikitable" style="text-align:center;">
                    <caption>Eon films</caption>
                    <tr>
                        <th>Title</th>
                        <th>Year</th>
                        <th>Bond actor</th>
                        <th>Director</th>
                    </tr>
                    <tr>
                        <td><a href="/wiki/Dr._No_(film)">Dr. No</a></td>
                        <td>1962</td>
                        <td>Sean Connery</td>
                        <td>Terence Young</td>
                    </tr>
                    <tr>
                        <td><a href="/wiki/From_Russia_with_Love_(film)">From Russia with Love</a></td>
                        <td>1963</td>
                        <td>Sean Connery</td>
                        <td>Terence Young</td>
                    </tr>
                </table>
        </body>
    </html>
"""
INFOBOX_HTML = """
    <table class="infobox vevent">
        <tr>
            <th colspan="2" style="text-align:center;font-size:125%;font-weight:bold;">Dr. No</th>
        </tr>
        <tr>
            <td colspan="2" style="text-align:center;">
                <a href="/wiki/File:Dr_No_1962_poster.jpg" class="image">
                    <img alt="Dr No 1962 poster.jpg"
                    src="//upload.wikimedia.org/wikipedia/en/4/43/Dr._No_-_UK_cinema_poster.jpg"
                    width="220" height="320">
                </a>
            </td>
        </tr>
    </table>
    """


@pytest.mark.usefixtures("mock_request_url")
def test_main(tmp_path: Path) -> None:
    """Test main function with mock arguments."""
    json_path = tmp_path / "bond_films.json"
    csv_path = tmp_path / "bond_films.csv"
    args = [
        "--url",
        "https://example.com/bond_films",
        "--table",
        "Eon films",
        "--skip-posters",
        "--json",
        str(json_path),
        "--csv",
        str(csv_path),
        "-v",
    ]

    main(args)

    with Path.open(json_path, "r", encoding="utf-8") as fid:
        loaded_data: Any = json.load(fid)
    assert loaded_data is not None

    assert len(cast("list[Any]", loaded_data)) == LEN_OF_ROWS  # cast for type conformity
    assert loaded_data[0]["title"] == "Dr. No"
    assert loaded_data[0]["year"] == "1962"
    assert loaded_data[1]["title"] == "From Russia with Love"
    assert loaded_data[1]["year"] == "1963"


def test_extract_infobox_poster() -> None:
    """Test extraction of poster URL from infobox HTML."""
    soup = BeautifulSoup(INFOBOX_HTML, "html.parser")
    infobox = soup.find("table", {"class": "infobox vevent"})
    assert infobox is not None

    poster = extract_infobox_poster(infobox)
    assert poster is not None
    assert poster == "https://upload.wikimedia.org/wikipedia/en/4/43/Dr._No_-_UK_cinema_poster.jpg"


# TODO(jb): #001 mock network calls in this test  # noqa: FIX002
if False:

    def test_fetch_bond_posters():
        """Test fetching of Bond posters from mock HTML.

        This is actually getting the image link from Wikipedia.
        """
        soup = BeautifulSoup(MOCK_HTML, "html.parser")  # instead of get_html(URL)
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
        "https://example.com/bond_films",
        "--table",
        "Eon films",
        "--json",
        "bond_films.json",
        "--csv",
        "bond_films.csv",
    ]
    args = parse_arguments(arg_list)

    assert args.url == "https://example.com/bond_films"
    assert args.json == "bond_films.json"
    assert args.csv == "bond_films.csv"


def test_map_headers() -> None:
    """Test mapping of table headers to expected keys."""
    expected_map = {"title": 0, "year": 1, "bond actor": 2, "director": 3}
    soup = BeautifulSoup(MOCK_HTML, "html.parser")  # instead of get_html(URL)
    tbl = find_table_by_caption(soup, "Eon films")
    assert tbl is not None

    first_tr = tbl.find("tr")
    assert first_tr is not None

    header_map = map_headers(first_tr)
    assert header_map == expected_map


def test_extract_table_rows() -> None:
    """Test extraction of table rows from mock HTML."""
    soup = BeautifulSoup(MOCK_HTML, "html.parser")  # instead of get_html(URL)
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


def test_cell_text_and_link() -> None:
    """Test extraction of text and link from a table cell."""
    soup = BeautifulSoup(MOCK_HTML, "html.parser")  # instead of get_html(URL)
    tbl = find_table_by_caption(soup, "Eon films")
    assert tbl is not None

    first_row = tbl.find_all("tr")[1]  # Skip header row
    row_cells = first_row.find_all(["th", "td"])
    assert row_cells is not None

    # Extract text and link from the first cell
    title_cell = cell_text_and_link(row_cells[0])["text"]
    link_cell = cell_text_and_link(row_cells[0])["link"]
    assert title_cell == "Dr. No"
    assert link_cell == "https://en.wikipedia.org/wiki/Dr._No_(film)"


def test_configure_logging(caplog: pytest.LogCaptureFixture) -> None:
    """Test logging configuration based on verbosity level."""
    # The actual logging configuration is not easily testable without inspecting the logger state
    # directly, which I'm not sure how to do cleanly.
    # However, we can check the logging output via the caplog fixture..nice!
    caplog.set_level(LOGGING_LEVEL)
    log_levels = [logging.WARNING, logging.INFO, logging.DEBUG]
    verbose_level = log_levels.index(logging.DEBUG)

    configure_logging(verbose_level)
    assert f"Log level set to {logging.getLevelName(logging.DEBUG)}" in caplog.text


def test_save_json(tmp_path: Path) -> None:
    """Test saving JSON data to a file."""
    data: list[dict[str, str | int]] = [
        {"title": "Dr. No", "year": 1962},
        {"title": "From Russia with Love", "year": 1963},
    ]
    file_path = tmp_path / "bond_films.json"
    save_json(data, file_path)

    # Verify the file was created and contains the correct data
    assert file_path.exists()
    with Path.open(file_path, "r", encoding="utf-8") as f:
        loaded_data = json.load(f)
    assert loaded_data == data


def test_save_csv(tmp_path: Path) -> None:
    """Test saving CSV data to a file."""
    data: list[dict[str, str | int]] = [
        {"title": "Dr. No", "year": 1962},
        {"title": "From Russia with Love", "year": 1963},
    ]
    file_path = tmp_path / "bond_films.csv"
    save_csv(data, file_path)

    # Verify the file was created and contains the correct data
    assert file_path.exists()
    with Path.open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        loaded_data = list(reader)
    assert loaded_data == [{"title": "Dr. No", "year": "1962"}, {"title": "From Russia with Love", "year": "1963"}]


def test_parse_table() -> None:
    soup = BeautifulSoup(MOCK_HTML, "html.parser")  # instead of get_html(URL)
    # soup_obj = soup.find_all("table")
    tbl = find_table_by_caption(soup, "Eon films")
    assert tbl is not None

    rows = parse_table(tbl)
    assert len(rows) == LEN_OF_ROWS
    first = rows[0]
    assert first["title"] == "Dr. No"
    assert first["year"] == "1962"
    assert first["bond actor"] == "Sean Connery"
    assert first["director"] == "Terence Young"


def test_find_table_by_caption() -> None:
    """Find a table by its caption in a BeautifulSoup object."""
    soup = BeautifulSoup(MOCK_HTML, "html.parser")  # instead of get_html(URL)
    assert soup is not None

    table = find_table_by_caption(soup, table_caption="Eon films", table_class=DEFAULT_TABLE_CLASS)
    assert table is not None
    assert table.name == "table"

    caption = table.find("caption")
    assert caption is not None
    assert caption.text.strip() == "Eon films"


@pytest.fixture(name="mock_request_url")  # Prevent "Unused function argument (RuffARG001)"
def mock_request_url(mocker: MockerFixture) -> mock.MagicMock:
    """Mock the request_url function to return predefined HTML content."""
    request_url = mocker.patch("src.james_bond.extract_bond_films.request_url")
    request_url.text = MOCK_HTML
    request_url.content = MOCK_HTML
    request_url.encoding = "utf-8"
    request_url.return_value = request_url
    request_url.status_code = STATUS_CODE_OK
    return request_url


@pytest.mark.usefixtures("mock_request_url")
def test_mocked_request_url() -> None:
    resp = request_url(TEST_URL)
    assert resp.status_code == STATUS_CODE_OK

    # Confirm it is valid data
    soup = BeautifulSoup(resp.text, "html.parser")
    assert soup is not None
    title = soup.find("title")
    assert title is not None
    assert title.text == "Example Domain"


@pytest.mark.usefixtures("mock_request_url")
def test_get_html() -> None:
    """Fetch URL and return a BeautifulSoup parsed document."""
    resp = get_html(TEST_URL)
    assert resp is not None

    # Confirm it is valid data
    title = resp.find("title")
    assert title is not None
    assert title.text == "James Bond Films"


# Useful links for testing requests package:
# <https://gist.github.com/evansde77/45467f5a7af84d2a2d34f3fcb357449c>
# <https://developers.lseg.com/en/article-catalog/article/getting-start-unit-test-with-pytest-for-an-http-rest-python-appl>
# Not used, but this looks useful: <https://github.com/getsentry/responses>
@mock.patch("requests.get")
def test_request_url_ok(mock_request: mock.Mock) -> None:
    mock_resp = requests.models.Response()
    mock_resp.status_code = 200
    mock_request.return_value = mock_resp

    res = request_url(TEST_URL)
    assert res.status_code == STATUS_CODE_OK


@mock.patch("requests.get")
def test_request_url_error(mock_request: mock.Mock) -> None:
    mock_resp = requests.models.Response()
    mock_resp.status_code = 401
    mock_request.return_value = mock_resp

    with pytest.raises(requests.exceptions.HTTPError) as err_msg:
        request_url(TEST_URL, timeout=10)
    assert "401" in str(err_msg.value)
