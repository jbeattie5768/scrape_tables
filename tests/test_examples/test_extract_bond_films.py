"""Unit tests for the Bond Films table extraction.

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
from bs4 import BeautifulSoup
from bs4.element import Tag

# Import as package name from src layout
from scrape_tables.examples.extract_bond_films import (
    DEFAULT_DELAY,
    extract_infobox_poster,
    fetch_bond_posters,
    main,
    parse_arguments,
)
from scrape_tables.scrapers.scrape_wiki_table import (
    parse_table,
)
from tests.fixtures import (
    TEST_HTML,
    TEST_HTML_INFOBOX,
    TEST_HTML_INFOBOX_2,
    TEST_HTML_INFOBOX_3,
    TEST_HTML_INFOBOX_NO_IMG,
    TEST_HTML_INFOBOX_NO_SRC,
    TEST_URL,
)

# CONSTANTS
LEN_OF_ROWS = 2  # update this if the number of rows in the test-table changes
DEFAULT_TABLE_CLASS = "wikitable"
DEFAULT_INFOBOX_CLASS = "infobox vevent"


@responses.activate
def test_main(tmp_path: Path) -> None:
    """Test main function.

    This uses the responses library to mock the requests.get() functionality.
    """
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
        _raw = json.load(fid)
    assert _raw is not None
    assert isinstance(_raw, list)
    loaded_json_data = cast("list[dict[str, str | int]]", _raw)  # cast for type conformity
    assert len(loaded_json_data) == LEN_OF_ROWS
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
    """Test main function when table is missing.

    This uses the responses library to mock the requests.get() functionality.
    """
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
        "Missing Table",  # sys.exit(1) when table is missing
        "--skip-posters",
        "--json",
        str(json_path),
        "--csv",
        str(csv_path),
        "-v",
    ]

    with pytest.raises(SystemExit) as exc:
        main(args)

    assert isinstance(exc.value.code, int)
    assert exc.value.code == 1
    assert not json_path.exists()
    assert not csv_path.exists()


def test_main_calls_fetch_posters(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Ensure `main()` calls `fetch_bond_posters` when `--skip-posters` is not set."""
    called: dict[str, bool] = {"called": False}

    def fake_fetch(_rows: list[dict[str, str]], delay: float = 0.0) -> None:
        _ = delay  # mark args as used to avoid linter complaints
        called["called"] = True

    def mock_get_html(_url: str) -> BeautifulSoup:
        return BeautifulSoup(TEST_HTML, "html.parser")

    monkeypatch.setattr("scrape_tables.examples.extract_bond_films.fetch_bond_posters", fake_fetch)
    monkeypatch.setattr("scrape_tables.scrapers.scrape_wiki_table.get_html", mock_get_html)

    json_path = tmp_path / "bond_films.json"
    csv_path = tmp_path / "bond_films.csv"
    args = [
        "--url",
        TEST_HTML,
        "--table",
        "Eon films",
        "--json",
        str(json_path),
        "--csv",
        str(csv_path),
    ]

    main(args)
    assert called["called"], "fetch_bond_posters was not called by main()"


def test_fetch_bond_posters_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure fetch_bond_posters continues when get_html() raises for one film."""

    def mock_get_html(url: str) -> BeautifulSoup:
        # Simulate network error for the first film
        if "Dr._No" in url:
            msg = "Simulated network error"
            raise requests.exceptions.RequestException(msg)  # failed to fetch film page
        return BeautifulSoup(TEST_HTML_INFOBOX_3, "html.parser")  # valid infobox for the other film

    # Get a Table of Rows from HTML
    soup = BeautifulSoup(TEST_HTML, "html.parser")
    table = soup.find("table", {"class": DEFAULT_TABLE_CLASS})
    assert table is not None
    rows = parse_table(table)
    assert rows

    monkeypatch.setattr("scrape_tables.scrapers.scrape_wiki_table.get_html", mock_get_html)
    fetch_bond_posters(rows, delay=0)  # should not raise

    # First row failed to fetch poster, second succeeded
    assert rows[0].get("_poster_link") is None or "_poster_link" not in rows[0]
    assert rows[1].get("_poster_link") is not None


def test_fetch_bond_posters_continues_on_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """If get_html raises ValueError for a film, fetch_bond_posters should continue."""

    def mock_get_html(url: str) -> BeautifulSoup:
        if "Dr._No" in url:
            msg = "Simulated parse error"
            raise ValueError(msg)
        return BeautifulSoup(TEST_HTML_INFOBOX_3, "html.parser")  # valid infobox for the other film

    # Get a Table of Rows from HTML
    soup = BeautifulSoup(TEST_HTML, "html.parser")
    table = soup.find("table", {"class": DEFAULT_TABLE_CLASS})
    assert isinstance(table, Tag)
    rows = parse_table(table)
    assert rows

    monkeypatch.setattr("scrape_tables.scrapers.scrape_wiki_table.get_html", mock_get_html)

    fetch_bond_posters(rows, delay=0)  # should not raise; second row will get a poster
    assert rows[1].get("_poster_link") is not None


def test_fetch_bond_posters_respects_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    """Passing a positive delay should call time.sleep()."""

    def mock_get_html(_url: str) -> BeautifulSoup:
        return BeautifulSoup(TEST_HTML_INFOBOX_3, "html.parser")

    def fake_sleep(s: float) -> None:
        sleep_calls.append(s)

    # Get a Table of Rows from HTML
    soup = BeautifulSoup(TEST_HTML, "html.parser")
    table = soup.find("table", {"class": DEFAULT_TABLE_CLASS})
    assert isinstance(table, Tag)
    rows = parse_table(table)
    assert rows

    sleep_calls: list[float] = []
    monkeypatch.setattr("scrape_tables.scrapers.scrape_wiki_table.get_html", mock_get_html)
    monkeypatch.setattr("time.sleep", fake_sleep)

    fetch_bond_posters(rows, delay=0.01)
    # Ensure sleep was called at least once (for the processed rows with links)
    assert sleep_calls, "time.sleep was not called for positive delay"


def test_fetch_bond_posters_no_infobox(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    """If the film page has no infobox table, fetch_bond_posters should log a warning and skip."""
    caplog.set_level(logging.WARNING)
    # Not using TEST_ROW_DATA as don't want to corrupt it
    rows = [{"title": "Dr. No", "_title_link": "https://example.com/Dr._No"}]

    def fake_get_html(_url: str) -> BeautifulSoup:
        return BeautifulSoup(TEST_HTML, "html.parser")  # TEST_HTML has no infobox

    monkeypatch.setattr("scrape_tables.scrapers.scrape_wiki_table.get_html", fake_get_html)

    fetch_bond_posters(rows, delay=0)
    assert "No infobox table found in" in caplog.text
    assert "_poster_link" not in rows[0]


def test_fetch_bond_posters_no_image(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    """When the film page contains an infobox with no image, fetch_bond_posters should warn about failure."""
    caplog.set_level(logging.WARNING)
    rows = [{"title": "Dr. No", "_title_link": "https://example.com/Dr._No"}]

    def fake_get_html(_url: str) -> BeautifulSoup:
        return BeautifulSoup(TEST_HTML_INFOBOX_NO_IMG, "html.parser")  #  no infobox image

    monkeypatch.setattr("scrape_tables.scrapers.scrape_wiki_table.get_html", fake_get_html)

    fetch_bond_posters(rows, delay=0)
    assert "Fetch Poster failure for" in caplog.text
    assert "_poster_link" not in rows[0]


def test_fetch_bond_posters_no_title_link(caplog: pytest.LogCaptureFixture) -> None:
    """If a row has no `_title_link`, the function should skip it and log a warning."""
    caplog.set_level(logging.WARNING)
    rows = [{"title": "No Link Row"}]

    # Should not raise and should log a warning
    fetch_bond_posters(rows, delay=0)
    assert "No title link for" in caplog.text
    assert "_poster_link" not in rows[0]


def test_extract_infobox_poster_double_slash() -> None:
    """Test extraction of poster double-slash (//) URL from infobox test HTML."""
    soup = BeautifulSoup(TEST_HTML_INFOBOX, "html.parser")
    infobox = soup.find("table", {"class": DEFAULT_INFOBOX_CLASS})
    assert infobox is not None

    poster = extract_infobox_poster(infobox)  # code: if src.startswith("//"):
    assert poster is not None
    assert poster == "https://upload.wikimedia.org/wikipedia/en/4/43/Dr._No_-_UK_cinema_poster.jpg"


def test_extract_infobox_poster_single_slash() -> None:
    """Test extraction of poster single-slash (/) URL from infobox test HTML."""
    soup = BeautifulSoup(TEST_HTML_INFOBOX_2, "html.parser")
    infobox = soup.find("table", {"class": DEFAULT_INFOBOX_CLASS})
    assert infobox is not None

    poster = extract_infobox_poster(infobox)  # code: if src.startswith("/"):
    assert poster is not None
    assert poster == "https://en.wikipedia.org/wiki/File:Dr._No_-_UK_cinema_poster.jpg"


def test_extract_infobox_poster_qualified() -> None:
    """Test extraction of fully-qualified (https://) poster URL from infobox test HTML."""
    soup = BeautifulSoup(TEST_HTML_INFOBOX_3, "html.parser")
    infobox = soup.find("table", {"class": DEFAULT_INFOBOX_CLASS})
    assert infobox is not None

    poster = extract_infobox_poster(infobox)  # code: return src
    assert poster is not None
    assert poster == "https://upload.wikimedia.org/wikipedia/en/a/ad/From_Russia_with_Love_-_UK_cinema_poster.jpg"


def test_extract_infobox_poster_no_infobox(caplog: pytest.LogCaptureFixture) -> None:
    """Test extraction of poster URL from HTML with no infobox."""
    infobox = None
    caplog.set_level(logging.WARNING)
    assert extract_infobox_poster(None) is None
    assert "Infobox is None" in caplog.text

    poster = extract_infobox_poster(infobox)
    assert poster is None


def test_extract_infobox_poster_no_image(caplog: pytest.LogCaptureFixture) -> None:
    """Test extraction of poster URL without image from infobox test HTML."""
    caplog.set_level(logging.DEBUG)  # debug level to capture at
    soup = BeautifulSoup(TEST_HTML_INFOBOX_NO_IMG, "html.parser")
    infobox = soup.find("table", {"class": DEFAULT_INFOBOX_CLASS})
    assert infobox is not None

    poster = extract_infobox_poster(infobox)
    assert poster is None
    assert "No image found in infobox" in caplog.text


def test_extract_infobox_poster_no_src(caplog: pytest.LogCaptureFixture) -> None:
    """Test extraction of poster URL from infobox test HTML."""
    caplog.set_level(logging.DEBUG)
    soup = BeautifulSoup(TEST_HTML_INFOBOX_NO_SRC, "html.parser")
    infobox = soup.find("table", {"class": DEFAULT_INFOBOX_CLASS})
    assert infobox is not None

    poster = extract_infobox_poster(infobox)
    assert poster is None
    assert "No image found in infobox" in caplog.text


def test_fetch_bond_posters(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test fetching of Bond posters from mocked HTML."""

    def mock_get_html(url: str) -> BeautifulSoup:
        name = url.split("/")[-1]
        if "Dr._No" in name:
            return BeautifulSoup(TEST_HTML_INFOBOX, "html.parser")
        if "From_Russia_with_Love" in name:
            return BeautifulSoup(TEST_HTML_INFOBOX_3, "html.parser")
        # default empty page (no infobox)
        return BeautifulSoup("", "html.parser")

    # # Get a Table of Rows from HTML
    soup = BeautifulSoup(TEST_HTML, "html.parser")
    table = soup.find("table", {"class": DEFAULT_TABLE_CLASS})
    assert table is not None
    rows = parse_table(table)
    assert rows

    monkeypatch.setattr("scrape_tables.scrapers.scrape_wiki_table.get_html", mock_get_html)
    fetch_bond_posters(rows, delay=0)  # no delay as tested with mocked data

    assert any("_poster_link" in r for r in rows)
    assert rows[0].get("_poster_link") is not None
    assert rows[1].get("_poster_link") is not None


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
