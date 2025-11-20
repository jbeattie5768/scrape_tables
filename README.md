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

- `-u`/`--url`: URL of the HTML page to get

- `-t`/`--table`: caption of the table to extract (case-sensitive)

- `--skip-posters`: skip following title links to fetch posters

- `--delay`: delay in seconds between poster page requests (be polite)

- `-o`/`--json`: output JSON path (default is '/data/table_output.json')

- `--csv`: output CSV path (optional)

- `-v`/`--verbose`: logging verbosity: none=WARNING, -v=INFO, -vv=DEBUG"

Respect rate limits and be polite in scraping other peoples data: avoid being blocked or causing harm.

Ensure you have the ethical right to scrape the data.

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

- Using the default URL\
  uv run james-bond -t "Eon films" --skip-posters -o .\\data\\eon_films.json

## Generate Timeline

- Running from Timeline project root\
  cd W:\\dev\\projects\\timeline\
  uv run python .\\src\\parse_timeline_json.py -j W:\\dev\\projects\\scrape_tables\\data\\eon_films.json -d bond_films -t .\\data\\bond_timeline_template.html -o bond_timeline.html

### Pre-Commit

pre-commit run\
uv run pre-commit run --all-files # no staging required
uv run pre-commit run # only check staged files

#### Pre-commit Hooks (recommended)

It's recommended to use `pre-commit` to run linters and checks before committing. The repository already includes Ruff hooks (`ruff-check` and `ruff-format`) in `.pre-commit-config.yaml` which provide linting and formatting. To catch type regressions early, add MyPy as a pre-commit hook as well.

What to run locally:

```pwsh
# Install pre-commit into your environment once
uv add pre-commit

# Run all hooks against all files (useful after upgrading hooks)
uv run pre-commit run --all-files

# Run the default pre-commit hooks on staged files (automatic on commit)
git commit -m "..."
```

Suggested `.pre-commit-config.yaml` additions:

```yaml
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.18.2
    hooks:
      - id: mypy
        args: ["--config-file=pyproject.toml"]
        files: \.py$
```

Notes:

- Keep `ruff-format` to automatically format code on commit and `ruff-check` to lint.
- Avoid enabling `ruff-check --fix` by default unless you want fixes applied automatically on commit; prefer running `ruff check --fix` or CI automation for large-scale fixes.
- Pin hook `rev` versions in `.pre-commit-config.yaml` to get reproducible behaviour; update them periodically in a single commit and run `pre-commit autoupdate`.

## Type-Checking

- Pyright via Pylance with settings.json entry:

  - `"python.analysis.typeCheckingMode": "strict"`

- MyPy

  - Running MyPy without passing . allows MyPy to use the files list defined in `[tool.mypy]` in `pyproject.toml`, avoiding walking the repository root in a way that can trigger duplicate discovery.

  uv run mypy

  uv run mypy .\\src
  uv run mypy .\\tests
  uv run mypy --strict .\\src\\scrape_tables\\examples\\extract_bond_films.py
  uv run mypy --strict .\\src\\scrape_tables\\scrapers\\scrape_wiki_table.py

Project layout and type-checking

- **src-layout**: This project uses the `src/` layout where the package sources live under `src/scrape_tables`. Tests import the package as `scrape_tables.*` (not `src.scrape_tables.*`). This avoids duplicate-module discovery by linters/type-checkers and matches common packaging practices.

- **Running MyPy**: Prefer running `uv run mypy --strict` (no `.`) so MyPy uses the `files` and `mypy_path` settings in `pyproject.toml` (which maps `src` as the import root). If you prefer an explicit invocation, run:

```pwsh
uv run mypy --strict src tests
```

This explicit command also avoids walking the project root and prevents duplicate module detection.

Robots, terms-of-use and rate-limiting

- When scraping external sites, always check the site's `robots.txt` and terms-of-service to ensure that scraping is permitted for your use case. Respect the site's crawl-delay directives and any API usage rules.
- Be polite: set a reasonable `--delay` between requests (default is `0.5s`), avoid high request rates, and add exponential backoff for 429/5xx responses when appropriate.
- If you plan to run the scraper at scale or in CI, consider caching or using site-provided APIs to avoid unnecessary load on third-party servers.

## PyTest

uv run pytest -rs -v\
uv run pytest .\\tests\\test_examples\\test_extract_bond_films.py -rs -v
uv run pytest .\\tests\\test_scrapers\\test_scrape_wiki_table.py -rs -v

_Note_: Do NOT use '--cov=.', you end up covering coverage
uv run pytest --cov=src. --cov-report html
uv run pytest .\\tests\\test_examples\\test_extract_bond_films.py --cov=src.scrape_tables.examples.extract_bond_films --cov-report html\
uv run pytest .\\tests\\test_scrapers\\test_scrape_wiki_table.py --cov=src.scrape_tables.scrapers.scrape_wiki_table --cov-report html
uv run pytest --cov=src. --cov-report=term-missing

## Run All Tests Locally

uv run ruff check . ; uv run mypy --strict ; uv run pytest ; uv run pytest --cov=src --cov-report=term-missing ; uv run pre-commit run --all-files

## Websites

<https://github.com/Sateesh110/Rep_Medium/blob/master/A1_WikiTables_Scraping/.ipynb>
