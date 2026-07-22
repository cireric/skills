.PHONY: url2md clean help

ifeq ($(OS),Windows_NT)
PYTHON := .venv/Scripts/python.exe
PIP    := .venv/Scripts/pip.exe
else
PYTHON := .venv/bin/python
PIP    := .venv/bin/pip
endif

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "CLI tools:"
	@echo "  url2md <url> [flags]  Crawl URL to Markdown"
	@echo "  url2md-preflight      Check url2md dependencies"
	@echo ""
	@echo "Maintenance:"
	@echo "  clean                 Remove caches and temp files"

# ---- url2md ----

url2md:
	$(PYTHON) scripts/url2md/crawl.py $(filter-out $@,$(MAKECMDGOALS))

url2md-preflight:
	$(PYTHON) scripts/url2md/crawl.py --preflight

# pass-through any unknown target so url2md flags work
%:
	@:

# ---- Maintenance ----

clean:
	@echo "Cleaning caches and temp files..."
ifeq ($(OS),Windows_NT)
	@if exist .pytest_cache rd /s /q .pytest_cache
	@if exist .playwright-mcp rd /s /q .playwright-mcp
	@if exist .coverage del /q .coverage
	@if exist htmlcov rd /s /q htmlcov
	@for /d %%d in (__pycache__) do @if exist %%d rd /s /q %%d
	@for /d %%d in (skills\info-collector\__pycache__) do @if exist %%d rd /s /q %%d
	@for /d %%d in (skills\info-collector\lib\__pycache__) do @if exist %%d rd /s /q %%d
	@for /d %%d in (skills\info-collector\tests\__pycache__) do @if exist %%d rd /s /q %%d
else
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .coverage htmlcov .playwright-mcp
endif
	@echo "Done."
