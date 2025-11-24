# Justfile for my convenience

# Cross platform shebang:
shebang := if os() == 'windows' {
  'pwsh.exe'
} else {
  '/usr/bin/env pwsh'
}
# Set shell for non-Windows OSs:
set shell := ["powershell", "-c"]
# Set shell for Windows OSs (assumes PowerShell Core):
set windows-shell := ["pwsh.exe", "-NoLogo", "-Command"]

# Runs:  just --list
list:
  just --list

# Does:  Displays PowerShell Core Version
psver:
    pwsh --version

# Runs:  uv venv <options>
venv Args="":
  uv venv {{Args}}

# Runs:  uv python upgrade <options>, uv sync --upgrade, uv run pre-commit autoupdate
upgrade Args="":
  uv python upgrade {{Args}}
  uv sync --upgrade
  uv run pre-commit autoupdate

# Runs:  uv sync <options>
sync Args="":
  uv sync {{Args}}

# Does:  Install pre-commit hooks and development project dependencies
install:
    uv run pre-commit install --install-hooks
    uv sync --dev --frozen

# Usage: just clean all|build|cache|data|docs|py|test|venv (defaults only)
clean Args="":
    just clean-{{Args}}

# Does:  Removes named Venv
clean-venv Args=".venv":
    if (Test-Path {{Args}}) { Remove-Item {{Args}} -Recurse -Force -ErrorAction SilentlyContinue }

# Does:  Removes caches - .cache, .ruff_cache, .pytest_cache, mypy_cache, __pycache__, etc
clean-cache:
    Get-ChildItem -Recurse -Filter '.cache' | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Recurse -Filter '.*_cache' | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue # .ruff_cache, .pytest_cache, etc
    Get-ChildItem -Recurse -Filter '*_cache' | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue # mypy_cache, etc
    Get-ChildItem -Recurse | where {$_.name -Match '__pycache__'} | Remove-Item -Force -Recurse -ErrorAction SilentlyContinue

# Does:  Removes Python compiled files - .pyc, .pyo
clean-py:
    Get-ChildItem -Recurse -Filter '*.pyc' | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Recurse -Filter '*.pyo' | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# Does:  Removes build files - dist/, .eggs/, *.egg-info
clean-build:
    #!{{shebang}}
    $buildFilePath = 'dist', '.eggs', '*.egg-info'
    foreach($filePath in $buildFilePath) {
        if (Test-Path $filePath) {
            Remove-Item -Force -Recurse -ErrorAction SilentlyContinue $filePath 2>$null
        }
    }

# Does:  Removes test files - .tox/, .coverage, htmlcov/, coverage.xml
clean-test:
    #!{{shebang}}
    $testFilePath = '.tox/', '.coverage', 'htmlcov/', 'coverage.xml'
    foreach($filePath in $testFilePath) {
        if (Test-Path $filePath) {
            Remove-Item -Force -Recurse -ErrorAction SilentlyContinue $filePath 2>$null
        }
    }

# Does:  Removes documentation output directory, e.g. ./docs
clean-docs Args="./docs":
    if (Test-Path {{Args}}) { Remove-Item {{Args}} -Recurse -Force -ErrorAction SilentlyContinue }

# Does:  Removes output directory and files, e.g. ./data
clean-data Args="./data":
    if (Test-Path {{Args}}) { Remove-Item {{Args}} -Recurse -Force -ErrorAction SilentlyContinue }

# Calls: clean-venv clean-cache clean-py clean-build clean-test clean-data clean-docs (defaults only)
clean-all: clean-venv clean-cache clean-py clean-build clean-test clean-data clean-docs

alias type:=mypy
# Runs:  uv run mypy <options>
mypy Args="--strict":
    uv run mypy {{Args}}

# Runs:  uv run mypy <options> src
mypy-src Args="--strict":
    uv run mypy {{Args}} src

# Runs:  uv run mypy <options> tests
mypy-tests Args="--strict":
    uv run mypy {{Args}} tests

alias pre:=pre-commit
# Runs:  uv run pre-commit run --all-files
pre-commit:
    uv run pre-commit run --all-files

alias tests:=test
# Runs:  uv run pytest <options>
test Args="-rs -v":
    uv run pytest {{Args}}

alias cov:=test-coverage
alias test-cov:=test-coverage
# Runs:  uv run pytest -vvv --cov=src. --cov-report=<option>
test-coverage Args="term-missing":
    uv run pytest -vvv --cov=src. --cov-report={{Args}}

alias cov-serve:=coverage-serve
alias serve-cov:=coverage-serve
# Does:  Serve the coverage report with a simple HTTP server
coverage-serve Args="8000":
    echo "Serving coverage report at http://localhost:{{Args}}/"
    uv run -m http.server {{Args}} -d "htmlcov"
    # Start-Sleep -Seconds 1
    # Start-Process "http://localhost:{{Args}}/"

# Runs:  uv run pytest -vvv --cov=src. --capture=no
test-verbose:
    uv run pytest -vvv --cov=src. --capture=no

# Runs:  uv run pytest <path> -rs -v
test-examples Args="./tests/test_examples":
    uv run pytest {{Args}} -rs -v

# Runs:  uv run pytest <path> -rs -v
test-scrapers Args="./tests/test_scrapers":
    uv run pytest {{Args}} -rs -v

# Does:  Run 'check' for all compatible Python versions
test-all:
    just check
    @pyv=("3.11" "3.12" "3.13" "3.14"); \
    for py in "${pyv[@]}"; do \
        echo "${py}"; \
        uv run -p "${py}" pytest -v --cov="src"; \
    done

# Runs:  uv run ruff <options>
ruff Args="check":
    uv run ruff {{Args}}

# Runs:  uv run ruff format <options>
format Args="--check ." :
    uv run ruff format {{Args}}

# Runs:  uv run ruff format --diff
format-diff:
    uv run ruff format --diff

# Calls: ruff format (defaults only)
lint: ruff format

# Runs:  uv run deptry <path>
deptry Args=".":
    uv run deptry {{Args}}

# Calls: mypy ruff  (defaults only)
typecheck: mypy ruff

# Calls: ruff format mypy test-cov pre-commit (defaults only)
check: ruff format mypy test-coverage pre-commit

# Does:  Counts Python files and lines per file in specified folders
count-files Args="@('./src','./tests')":
    #!{{shebang}}
    $src_folders = {{Args}}
    $tbl = Get-ChildItem -Path $src_folders -Recurse -Filter *.py -File -ErrorAction SilentlyContinue
    $results = foreach ($file in $tbl) {
        $lines = (Get-Content -LiteralPath $file.FullName -ErrorAction SilentlyContinue | Measure-Object -Line).Lines
        [PSCustomObject]@{ File = $file.FullName; Lines = $lines }
    }
    $results | Sort-Object -Property Lines -Descending | Format-Table @{Label='File';Expression={$_.File}}, @{Label='Lines';Expression={$_.Lines}} -AutoSize
    echo "Total files: $($tbl.Count)        Total lines: $($results | Measure-Object -Property Lines -Sum | Select-Object -ExpandProperty Sum)"

# Runs:  uv build <options>
build Args="--no-cache":
    uv build {{Args}}

alias act:=gact
# Does:  Runs GitHub Actions locally via 'act'
gact Args="":
    #!{{shebang}}
    # Check for docker running
    # $dockerStatus = (Get-Service -Name 'docker' -ErrorAction SilentlyContinue).Status
    $dockerRunning = Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue
    if ($dockerRunning -eq $null) {
        echo "Docker is not running. Please start Docker and try again."
    } else {
        act {{Args}}
    }

run Args="":
    just run-{{Args}}

# Runs:  uv run james-bond -t "Eon films" <options. -o ./data/bond_eon_films.json
run-bond Args="--skip-posters":
    uv run james-bond -t "Eon films" {{Args}} -o ./data/bond_eon_films.json

# Runs:  uv run --with pdoc pdoc ./src -o ./docs
docs:
    just docs-gen
    just docs-serve

docs-gen:
    uv run --with pdoc pdoc ./src -o ./docs  # Experimental use at the moment

alias serve-docs:=docs-serve
# Does:  Serve the documentation with a simple HTTP server
docs-serve Args="12001":
    echo "Serving docs at http://localhost:{{Args}}/"
    uv run -m http.server {{Args}} -d "docs"
    # Start-Sleep -Seconds 1
    # Start-Process "http://localhost:{{Args}}/"
