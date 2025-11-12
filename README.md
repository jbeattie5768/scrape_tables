# Eon films extractor

This small Python script extracts the "Eon films" table from Wikipedia and writes a JSON file with fields: `title`, `year`, `bond_actor`, `director`, and `poster`.

Usage

Run the script with Python. The script includes a simple CLI:

- `-v` / `--verbose`: increase logging (repeat for more verbosity)
- `--threshold N`: maximum number of missing posters before following title links. `0` means follow all links.
- `-o PATH` / `--output PATH`: output JSON path (default `w:\eon_films.json`)
- `--csv PATH`: optional CSV output path
- `--skip-posters`: skip fetching poster images (faster, no network)
- `--delay`: float seconds to wait between poster page requests (be polite)

Example

```bash
python extract_bond.py -v --threshold 0 -o "w:\eon_films.json"
```

Dependencies

See `requirements.txt`. Install with:

```bash
pip install -r requirements.txt
```

______________________________________________________________________

`uv run --with requests --with beautifulsoup4 python "w:\extract_bond.py" -v --threshold 0 -o "w:\eon_films.json"`

`uv run --with requests --with beautifulsoup4 python w:/extract_bond.py --skip-posters -o w:/eon_films.json`

`uv run --with pytest --with requests --with beautifulsoup4 python -m pytest -q tests/test_extract_bond.py`

`uv run --with requests --with beautifulsoup4 --with pytest python -m pytest -q tests/test_extract_bond.py`

`uv run --with flake8 --with pytest --with requests --with beautifulsoup4 python -c "import sys, subprocess; print('Linting...'); code=subprocess.call(['flake8','w:/extract_bond.py','w:/tests','--max-line-length=120']); print('Running tests...'); code2=subprocess.call(['pytest','-q','tests/test_extract_bond.py']); sys.exit(code or code2)"`

`uv run --with ruff python -c "import subprocess, sys; print('Running ruff...'); sys.exit(subprocess.call(['ruff','check','w:/extract_bond.py','w:/tests','--line-length','120']))"`

`uv run --with requests --with beautifulsoup4 python w:/extract_bond.py -v --skip-posters -o w:/eon_films.json`

`uv run --with requests --with beautifulsoup4 python w:/extract_bond.py -v --threshold 0 --delay 2 -o w:/eon_films.json`

`uv run james-bond --skip-posters -o .\data\eon_films.json`

______________________________________________________________________

## Generate James Bond Films

uv run james-bond -t "Eon films" --skip-posters -o .\\data\\eon_films.json

## Generate Timeline

`uv run python ./src/parse_timeline_json.py -j w:\eon_films.json -d bond_films -t ./data/bond_timeline_template.html -o bond_timeline.html`

### Pre-Commit

`pre-commit run`
`uv run pre-commit run`

## Type-Checking

- Pyright via Pylance with settings.json entry: `python.analysis.typeCheckingMode": "standard"`
- MyPy
  - mypy --strict .\\src\\james_bond\\extract_bond_films.py
  - uv run python -m mypy --strict .\\src\\james_bond\\extract_bond_films.py

## PyTest

- uv run python -m pytest -v

## Websites

<https://github.com/Sateesh110/Rep_Medium/blob/master/A1_WikiTables_Scraping/A1_WikiTable_WorldPopulation.ipynb>
