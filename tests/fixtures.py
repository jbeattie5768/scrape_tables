"""Test fixtures for scraping and extraction tests."""

TEST_URL = "https://example.com/bond_films"

TEST_ROWS_DATA = [
    {"title": "Dr. No", "year": "1962"},  # keep years as str for CSV comparison
    {"title": "From Russia with Love", "year": "1963"},
]

# Expected output for TEST_HTML
EXPECTED_HTML_HEADER = {
    "title": 0,
    "year": 1,
    "bond actor": 2,
    "director": 3,
    "ref(s)": 4,
}

TEST_HTML = """
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
                        <th>Ref(s)</th>
                    </tr>
                    <tr>
                        <td><a href="/wiki/Dr._No_(film)">Dr. No</a></td>
                        <td>1962</td>
                        <td>Sean Connery</td>
                        <td>Terence Young</td>
                        <td>[1][2]</td>
                    </tr>
                    <tr>
                        <td><a href="/wiki/From_Russia_with_Love_(film)">From Russia with Love</a></td>
                        <td>1963</td>
                        <td>Sean Connery</td>
                        <td>Terence Young</td>
                        <td>[3][4]</td>
                    </tr>
                </table>
        </body>
    </html>
"""

TEST_HTML_SHORT_ROW = """
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
                        <!-- Two Missing Rows -->
                    </tr>
                    <tr>
                        <td><a href="/wiki/From_Russia_with_Love_(film)">From Russia with Love</a></td>
                        <td>1963</td>
                        <!-- Two Missing Rows -->
                    </tr>
                </table>
        </body>
    </html>
"""
TEST_HTML_NO_ROWS = """
    <html>
        <head><title>James Bond Films</title></head>
            <body>
                <table class="wikitable" style="text-align:center;">
                    <caption>Eon films</caption>
                </table>
        </body>
    </html>
"""

TEST_HTML_INFOBOX = """  # URL type 1: with delimiter `//`
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

TEST_HTML_INFOBOX_2 = """  # URL type 2: with delimiter `/`
    <table class="infobox vevent">
        <tr>
            <th colspan="2" style="text-align:center;font-size:125%;font-weight:bold;">Dr. No</th>
        </tr>
        <tr>
            <td colspan="2" style="text-align:center;">
                <a href="/wiki/File:Dr_No_1962_poster.jpg" class="image">
                    <!-- The src URL is a page rather than an image -->
                    <img alt="Dr No 1962 poster.jpg"
                    src="/wiki/File:Dr._No_-_UK_cinema_poster.jpg"
                    width="220" height="320">
                </a>
            </td>
        </tr>
    </table>
    """

TEST_HTML_INFOBOX_3 = """  # URL type 3: fully qualified URL
    <table class="infobox vevent">
        <tr>
            <th colspan="2" style="text-align:center;font-size:125%;font-weight:bold;">Dr. No</th>
        </tr>
        <tr>
            <td colspan="2" style="text-align:center;">
                <a href="/wiki/File:From_Russia_with_Love_-_UK_cinema_poster.jpg" class="image">
                    <!-- The src URL is a direct fully qualified -->
                    <img alt="From Russia with Love poster.jpg"
                    src="https://upload.wikimedia.org/wikipedia/en/a/ad/From_Russia_with_Love_-_UK_cinema_poster.jpg"
                    width="220" height="320">
                </a>
            </td>
        </tr>
    </table>
    """

TEST_HTML_INFOBOX_NO_IMG = """
    <table class="infobox vevent">
        <tr>
            <th colspan="2" style="text-align:center;font-size:125%;font-weight:bold;">Dr. No</th>
        </tr>
        <tr>
            <td colspan="2" style="text-align:center;">
                <a href="/wiki/File:Dr_No_1962_poster.jpg" class="image">
                    <!-- No img tag here -->
                </a>
            </td>
        </tr>
    </table>
    """

TEST_HTML_INFOBOX_NO_SRC = """
    <table class="infobox vevent">
        <tr>
            <th colspan="2" style="text-align:center;font-size:125%;font-weight:bold;">Dr. No</th>
        </tr>
        <tr>
            <td colspan="2" style="text-align:center;">
                <a href="/wiki/File:Dr_No_1962_poster.jpg" class="image">
                    <!-- No 'src' attribute in <img> tag -->
                    <img >
                </a>
            </td>
        </tr>
    </table>
    """

# Expected output for TEST_HTML_2_HEADER_ROWS
TWO_ROW_EXPECTED_HEADER_MAP = {
    "title": 0,
    "year": 1,
    "bond actor": 2,
    "director": 3,
    "box office (millions) actual $": 4,
    "box office (millions) adjusted $ (2024)": 5,
    "budget (millions) actual $": 6,
    "budget (millions) adjusted $ (2024)": 7,
    "ref(s)": 8,
}

TEST_HTML_2_HEADER_ROWS = """
    <table class="wikitable" style="text-align:center;">
        <caption>Eon films</caption>
        <thead>
            <tr>
                <th rowspan="2">Title</th>
                <th rowspan="2">Year</th>
                <th rowspan="2">Bond actor</th>
                <th rowspan="2">Director</th>
                <th colspan="2">Box office (millions)</th>
                <th colspan="2">Budget (millions)</th>
                <th rowspan="2">Ref(s)</th>
            </tr>
            <tr>
                <th>Actual $</th>
                <th>Adjusted $ (2024)</th>
                <th>Actual $</th>
                <th>Adjusted $ (2024)</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><a href="/wiki/Dr._No_(film)">Dr. No</a></td>
                <td>1962</td>
                <td>Sean Connery</td>
                <td>Terence Young</td>
                <td>10</td>
                <td>100</td>
                <td>1</td>
                <td>10</td>
                <td>[1]</td>
            </tr>
        </tbody>
    </table>
    """
TEST_HTML_3_HEADER_ROWS = """
    <table>
        <tr>
            <th rowspan="3">Title</th>
            <th colspan="2">Group</th>
        </tr>
        <tr>
            <th>One</th>
            <th>Two</th>
        </tr>
        <tr>
            <th>Three</th>
            <th>Four</th>
        </tr>
    </table>
    """

TEST_HTML_EMPTY_ROW = """
    <table>
        <tr>
            <th>Title</th>
            <th>Year</th>
        </tr>
        <tr></tr>
        <tr>
            <td>Dr. No</td>
            <td>1962</td>
        </tr>
    </table>
    """
