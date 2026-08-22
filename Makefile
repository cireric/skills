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
	@echo "  clean                 Remove caches and temp files (cross-platform, keeps output/)"
	@echo "                        extra flags: scripts/cleanup.py --help"

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
	$(PYTHON) scripts/cleanup.py --keep-output
