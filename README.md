# Scrape Tables

This small Python script extracts tables from html sources

## Examples

There are a number of examples:

### James bond Films

Script that extracts the first "Eon films" captioned table from Wikipedia and writes a JSON file with fields: `title`, `year`, `bond_actor`, `director`, `_title_link`. Optionally it will add a `_poster_link` field.

An example JSON entry:

```json
  {
    "title": "Dr. No",
    "year": "1962",
    "bond actor": "Sean Connery",
    "director": "Terence Young",
    "box office (millions)": "59.5",
    "budget (millions)": "722.6",
    "ref(s)": "1.1",
    "_title_link": "https://en.wikipedia.org/wiki/Dr._No_(film)",
    "_poster_link": "https://upload.wikimedia.org/wikipedia/en/thumb/4/43/Dr._No_-_UK_cinema_poster.jpg/250px-Dr._No_-_UK_cinema_poster.jpg"
  },
```

The script includes a simple CLI:

- `-v` / `--verbose`: increase logging (repeat for more verbosity)

- `-o PATH` / `--output PATH`: output JSON path (default `w:\eon_films.json`)

- `--csv PATH`: optional CSV output path

- `--skip-posters`: skip fetching poster images (faster, no network)

- `--delay`: float seconds to wait between poster page requests (be polite)

- `-u`/`--url`: URL of the HTML page to get

- `-t`/`--table`: caption of the table to extract (case-sensitive)

- `--skip-posters`: skip following title links to fetch posters

- `--delay`: delay in seconds between poster page requests (be polite)

- `-o`/`--json`: output JSON path (default is .\\data\\table_output.json)

- `--csv`: output CSV path (optional)

- `-v`/`--verbose`: logging verbosity: none=WARNING, -v=INFO, -vv=DEBUG"

#### Example CLI

```pwsh
# Powershell
$ENV:URL = "https://en.wikipedia.org/wiki/List_of_James_Bond_films"
uv run python extract_bond_films.py -u URL -t "Eon films" --skip-posters -o .\data\eon_films\.json

# Using pyproject.toml script alias #james-bond'
uv run james-bond -u URL -t "Eon films" --skip-posters -o .\data\eon_films\.json
```

Dependencies

See `pyproject.toml`.

For UV:

```pwsh
# Sync uv environment with uv.lock file
uv sync  
```

..or with PIP:

```pwsh
# Install core dependencies into current environment
pip install .
```

______________________________________________________________________

`uv run --with requests --with beautifulsoup4 python "w:\extract_bond.py" -v --threshold 0 -o "w:\eon_films.json"`

`uv run --with requests --with beautifulsoup4 python w:\extract_bond.py --skip-posters -o w:\eon_films.json`

`uv run --with pytest --with requests --with beautifulsoup4 python -m pytest -q tests\test_extract_bond.py`

`uv run --with requests --with beautifulsoup4 --with pytest python -m pytest -q tests\test_extract_bond.py`

`uv run --with flake8 --with pytest --with requests --with beautifulsoup4 python -c "import sys, subprocess; print('Linting...'); code=subprocess.call(['flake8','w:\extract_bond.py','w:\tests','--max-line-length=120']); print('Running tests...'); code2=subprocess.call(['pytest','-q','tests\test_extract_bond.py']); sys.exit(code or code2)"`

`uv run --with ruff python -c "import subprocess, sys; print('Running ruff...'); sys.exit(subprocess.call(['ruff','check','w:\extract_bond.py','w:\tests','--line-length','120']))"`

`uv run --with requests --with beautifulsoup4 python w:\extract_bond.py -v --skip-posters -o w:\eon_films.json`

`uv run --with requests --with beautifulsoup4 python w:\extract_bond.py -v --threshold 0 --delay 2 -o w:\eon_films.json`

`uv run james-bond --skip-posters -o .\data\eon_films.json`

______________________________________________________________________

## Generate James Bond Films

- Using the default URL  
uv run james-bond -t "Eon films" --skip-posters -o .\\data\\eon_films.json

## Generate Timeline

- Running from Timeline project root  
cd W:\\dev\\projects\\timeline  
uv run python .\\src\\parse_timeline_json.py -j W:\\dev\\projects\\scrape_tables\\data\\eon_films.json -d bond_films -t .\\data\\bond_timeline_template.html -o bond_timeline.html

### Pre-Commit

pre-commit run  
uv run pre-commit run

## Type-Checking

- Pyright via Pylance with settings.json entry:
  - `"python.analysis.typeCheckingMode": "strict"`
- MyPy
  uv run mypy --strict .\\src\
  uv run mypy --strict .\\tests\
  uv run python -m mypy --strict .\\src\\scrape_tables\\examples\\extract_bond_films.py\
  uv run python -m mypy --strict .\\src\\scrape_tables\\scrapers\\scrape_wiki_table.py

## PyTest

uv run python -m pytest -rs -v\
uv run python -m pytest .\\tests\\test_extract_bond_films.py -rs -v\
uv run python -m pytest .\\tests\\test_extract_wiki_table.py -rs -v

_Note_: Do NOT use '--cov=.', you end up covering coverage\
uv run python -m pytest --cov=src. --cov-report html\
uv run python -m pytest .\\tests\\test_examples\\test_extract_bond_films.py --cov=src.scrape_tables.examples.extract_bond_films --cov-report html  
uv run python -m pytest .\\tests\\test_scrapers\\test_scrape_wiki_table.py --cov=src.scrape_tables.scrapers.scrape_wiki_table --cov-report html

## Websites

<https://github.com/Sateesh110/Rep_Medium/blob/master/A1_WikiTables_Scraping/A1_WikiTable_WorldPopulation.ipynb>
