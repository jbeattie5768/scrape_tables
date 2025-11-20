"""Test fixtures for scraping and extraction tests."""

TEST_URL = "https://example.com/bond_films"

TEST_ROWS_DATA = [
    {"title": "Dr. No", "year": "1962"},  # keep years as str for CSV comparison
    {"title": "From Russia with Love", "year": "1963"},
]

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
