"""Unit tests for the Bond table extractor.

These tests are intentionally minimal and avoid network access.
"""

import pytest
from bs4 import BeautifulSoup

from src.james_bond.extract_bond_films import find_eon_table, parse_table

LEN_OF_ROWS = 2  # Update this if the number of rows in the test-table changes


def test_parse_table_minimal() -> None:
    """Parse a minimal wikitable and verify expected fields are present."""
    html: str = """
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
"""

    soup_obj = BeautifulSoup(html, "html.parser")  # instead of get_html(URL)
    # soup_obj = soup.find_all("table")
    tbl = find_eon_table(soup_obj)
    if not tbl:
        pytest.fail("Eon films table not found.")
    # skip posters to avoid network access
    rows = parse_table(tbl, poster_threshold=999, skip_posters=True)
    assert isinstance(rows, list)
    assert len(rows) == LEN_OF_ROWS
    first = rows[0]
    assert first["title"] == "Dr. No"
    assert "poster" in first
    assert first["poster"] == ""
    assert "poster" in rows[1]
