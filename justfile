# Justfile for my convenience

# Cross platform shebang:
shebang := if os() == 'windows' {
  'pwsh.exe'
} else {
  '/usr/bin/env pwsh'
}
# Set shell for non-Windows OSs:
set shell := ["powershell", "-c"]

# Set shell for Windows OSs:
set windows-shell := ["pwsh.exe", "-NoLogo", "-Command"]

# set positional-arguments

# Runs: just --list
list:
  just --list

# Does: Displays PowerShell version
psver:
	#!{{shebang}}
	$PSV = $PSVersionTable.PSVersion | % {"$_" -split "\." }
	$psver = $PSV[0] + "." + $PSV[1]
	if ($PSV[2].Length -lt 4) {
		$psver += "." + $PSV[2] + " Core"
	} else {
		$psver += " Desktop"
	}
	echo "PowerShell $psver"

# Runs: uv venv <options>
venv *Args="":
  uv venv {{Args}}

# Runs: uv python upgrade <options>
upgrade *Args="":
  uv python upgrade {{Args}}

# Runs: uv sync <options>
sync *Args="":
  uv sync {{Args}}

# Usage: just clean all|build|cache|py|test|venv (defaults)
clean Args="":
    #!{{shebang}}
    if ("{{Args}}" -eq "") {
        just clean-all
    } else {
        just clean-{{Args}}
    }
# Does: Removes named Venv (default is .venv)
clean-venv Args=".venv":
    if (Test-Path {{Args}}) { Remove-Item {{Args}} -Recurse -Force -ErrorAction SilentlyContinue }

# Does: Removes caches - .cache, .ruff_cache, .pytest_cache, mypy_cache, __pycache__, etc
clean-cache:
    Get-ChildItem -Recurse -Filter '.cache' | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Recurse -Filter '.*_cache' | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue # .ruff_cache, .pytest_cache, etc
    Get-ChildItem -Recurse -Filter '*_cache' | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue # mypy_cache, etc
    Get-ChildItem -Recurse | where {$_.name -Match '__pycache__'} | Remove-Item -Force -Recurse -ErrorAction SilentlyContinue

# Does: Removes Python compiled files - .pyc, .pyo
clean-py:
    Get-ChildItem -Recurse -Filter '*.pyc' | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Recurse -Filter '*.pyo' | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# Does: Removes build files - dist/, .eggs/, *.egg-info
clean-build:
    #!{{shebang}}
    $buildFilePath = 'dist', '.eggs', '*.egg-info'
    foreach($filePath in $buildFilePath) {
        if (Test-Path $filePath) {
            Remove-Item -Force -Recurse -ErrorAction SilentlyContinue $filePath 2>$null
        }
    }

# Does: Removes test files - .tox/, .coverage, htmlcov/, coverage.xml
clean-test:
    #!{{shebang}}
    $testFilePath = '.tox', '.coverage', 'htmlcov', 'coverage.xml'
    foreach($filePath in $testFilePath) {
        if (Test-Path $filePath) {
            Remove-Item -Force -Recurse -ErrorAction SilentlyContinue $filePath 2>$null
        }
    }

# Does: Runs all clean tasks
clean-all: clean-venv clean-cache clean-py clean-build clean-test


alias type:=mypy
mypy Args="--strict":
    uv run mypy {{Args}}
mypy-src Args="--strict":
    uv run mypy {{Args}} src
mypy-tests Args="--strict":
    uv run mypy {{Args}} tests

alias pre:=pre-commit
pre-commit:
    uv run pre-commit run --all-files

alias tests:=test
alias cov:=test-cov
# Runs: uv run pytest <options> (default is -q)
test Args="-q":
    uv run pytest {{Args}}
# Runs: uv run pytest <options> --cov=src --cov-report=term-missing tests (default option is -q)
test-cov Args="-q":
    uv run pytest {{Args}} --cov=src --cov-report=term-missing tests

# Runs: uv run ruff <options> (default is check)
ruff Args="check":
    uv run ruff {{Args}}
# Runs: uv run ruff format <options> (default is --check)
format Args="--check" :
    uv run ruff format {{Args}}
# Runs: uv run ruff format --diff
format-diff:
    uv run ruff format --diff
# Runs: both default ruff and format
lint: ruff format

# Runs: both default mypy and ruff
typecheck: mypy ruff
# Runs: all default checks: ruff, format, mypy, test-cov, pre-commit
check: ruff format mypy test-cov pre-commit
