# Scrape-Tables Justfile for my convenience

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

# Ensure this is the first recipe
[doc("List all available recipes")]
_list:
  @just --list --unsorted

[doc("List Groups")]
_groups:
  @just --groups --unsorted

# ###########################################
# Environment Management
# ###########################################

[group("Environment")]
[doc("Python <args>, Sync local env, autoupdate pre-commit")]
install Args="3.14":
    uv python install {{Args}}
    uv sync --dev --frozen
    uv run pre-commit install --install-hooks

[group("Environment")]
sync Args="":
  uv sync {{Args}}

[group("Environment")]
venv Args="":
  uv venv {{Args}}

[group("Environment")]
[doc("Python <args>, Sync local env, autoupdate pre-commit")]
upgrade Args="":
  uv python upgrade {{Args}}
  uv sync --upgrade
  uv run pre-commit autoupdate

# ###########################################
# Cleaning Tasks
# ###########################################

[group("Clean")]
[doc("just clean all|build|cache|data|docs|py|test|venv")]
clean Args="":
    just clean-{{Args}}

[group("Clean")]
clean-all: clean-build clean-cache clean-data clean-docs clean-py  clean-test  clean-venv

[group("Clean")]
clean-build:
    #!{{shebang}}
    $buildFilePath = 'dist', '.eggs', '*.egg-info'
    foreach($filePath in $buildFilePath) {
        if (Test-Path $filePath) { Remove-Item -Force -Recurse -ErrorAction SilentlyContinue $filePath 2>$null }
    }

[group("Clean")]
clean-cache:
    Get-ChildItem -Recurse -Filter '.cache' | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Recurse -Filter '.*_cache' | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue # .ruff_cache, .pytest_cache, etc
    Get-ChildItem -Recurse -Filter '*_cache' | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue  # mypy_cache, etc
    Get-ChildItem -Recurse | where {$_.name -Match '__pycache__'} | Remove-Item -Force -Recurse -ErrorAction SilentlyContinue

[group("Clean")]
clean-data Args="./data":
    if (Test-Path {{Args}}) { Remove-Item {{Args}} -Recurse -Force -ErrorAction SilentlyContinue }

[group("Clean")]
clean-docs Args="./docs":
    if (Test-Path {{Args}}) { Remove-Item {{Args}} -Recurse -Force -ErrorAction SilentlyContinue }

[group("Clean")]
clean-py:
    Get-ChildItem -Recurse -Filter '*.pyc' | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Recurse -Filter '*.pyo' | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

[group("Clean")]
clean-test:
    #!{{shebang}}
    $testFilePath = '.tox/', '.coverage', 'htmlcov/', 'coverage.xml'
    foreach($filePath in $testFilePath) {
        if (Test-Path $filePath) { Remove-Item -Force -Recurse -ErrorAction SilentlyContinue $filePath 2>$null }
    }

[group("Clean")]
clean-venv Args=".venv":
    if (Test-Path {{Args}}) { Remove-Item {{Args}} -Recurse -Force -ErrorAction SilentlyContinue }

# ###########################################
# Quality Assurance Tasks
# ###########################################

[group("QA Checks")]
[doc("just ruff format mypy test-cov pre-commit")]
check: ruff format mypy test-coverage pre-commit

[group("QA Checks")]
[doc("just ruff format")]
lint: ruff format

# Further type-checkers might be used, eg. pyright, pyre, etc.
alias type:=typecheck
[group("QA Checks")]
[doc("just mypy")]
typecheck: mypy

[group("QA Checks")]
ruff Args="check":
    uv run ruff {{Args}}

[group("QA Checks")]
format Args="--check ." :
    uv run ruff format {{Args}}

[group("QA Checks")]
format-diff:
    uv run ruff format --diff

[group("QA Checks")]
[doc]
deptry Args=".":
    uv run deptry {{Args}}  # Deptry checks for unused dependencies

[group("QA Checks")]
mypy Args="--strict":
    uv run mypy {{Args}}

[group("QA Checks")]
mypy-src Args="--strict":
    uv run mypy {{Args}} src

[group("QA Checks")]
mypy-tests Args="--strict":
    uv run mypy {{Args}} tests

alias pre:=pre-commit
[group("QA Checks")]
pre-commit:
    uv run pre-commit run --all-files

# ###########################################
# Testing Tasks
# ###########################################

alias tests:=test
[group("Tests")]
test Args="-rs -v":
    uv run pytest {{Args}}

[group("Tests")]
test-examples Args="./tests/test_examples":
    uv run pytest {{Args}} -rs -v

[group("Tests")]
test-scrapers Args="./tests/test_scrapers":
    uv run pytest {{Args}} -rs -v

[group("Tests")]
[doc("-v, -vv or -vvv")]
test-verbose Args="-vvv":
    uv run pytest {{Args}} --cov=src. --capture=no

alias cov:=test-coverage
alias test-cov:=test-coverage
[group("Tests")]
[doc("Can change the report type")]
test-coverage Args="term-missing":
    uv run pytest -vvv --cov=src. --cov-report={{Args}}

alias cov-serve:=test-serve
alias serve-cov:=test-serve
[group("Tests")]
[doc("Simple HTTP server for Coverage ('./htmlcov')")]
test-serve Args="8000":
    #!{{shebang}}
    if (Test-Path "./htmlcov") {
        Write-Host "Serving coverage report at http://localhost:{{Args}}/"
        uv run -m http.server {{Args}} -d "htmlcov"
        # Start-Sleep -Seconds 1
        # Start-Process "http://localhost:{{Args}}/"
    } else {
        Write-Host "'htmlcov' directory not found. Please run 'just test-coverage' first."
    }

# ###########################################
# Build Tasks
# ###########################################

[group("Build")]
build Args="--no-cache":
    uv build {{Args}}

# ###########################################
# GitHub Actions
# ###########################################

alias act:=gact
[group("GitHub Actions")]
[doc("Runs GitHub Actions locally via 'act'")]
gact Args="":
    #!{{shebang}}
    $dockerRunning = Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue
    if ($dockerRunning -eq $null) {
        echo "Docker is not running. Please start Docker and try again."
    } else {
        act {{Args}}
    }

# ###########################################
# Run Examples
# ###########################################

[group("Run Examples")]
[doc("just run bond")]
run Args="":
    @just run-{{Args}}

[group("Run Examples")]
run-bond Args="--skip-posters":
    uv run james-bond -t "Eon films" {{Args}} -o ./data/bond_eon_films.json

# ###########################################
# Documentation Tasks
# ###########################################

[group("Docs")]
[doc("just docs-gen docs-serve")]
docs: docs-gen docs-serve

[group("Docs")]
docs-gen:
    @echo "Experimental: Generating docs into ./docs"
    uv run --with pdoc pdoc ./src -o ./docs

alias serve-docs:=docs-serve
[group("Docs")]
[doc("Simple HTTP server for './docs'")]
docs-serve Args="12001":
    #!{{shebang}}
    if (Test-Path "./docs") {
        Write-Host "Serving docs at http://localhost:{{Args}}/"
        uv run -m http.server {{Args}} -d "docs"
        # Start-Sleep -Seconds 1
        # Start-Process "http://localhost:{{Args}}/"
    } else {
        Write-Host "'./docs' directory not found. Please run 'just docs-gen' first."
    }

# ###########################################
# Miscellaneous Tasks
# ###########################################

[group("Misc")]
[doc("Count Py files and lines per file")]
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

[group("Misc")]
[doc("Display PowerShell Core Version")]
psver:
    pwsh --version

# ###########################################
# To Be Implemented Tasks (hidden)
# ###########################################

# alias test-vers:=test-versions
[group("Misc")]
[doc("Run 'just check' for all compatible Python versions")]
_test-versions:
    @echo "Not implemented yet."
