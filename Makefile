# Makefile for WimPyAmp

# Variables
PYTHON := python3
VENV_DIR := venv
VENV_PYTHON := $(VENV_DIR)/bin/python
VENV_PIP := $(VENV_DIR)/bin/pip
REQUIREMENTS := requirements.txt
VERSION := $(shell cat VERSION)

# Default target
.PHONY: all
all: setup run

# Setup virtual environment and install dependencies
.PHONY: setup
setup:
	$(PYTHON) -m venv $(VENV_DIR)
	$(VENV_PIP) install -r $(REQUIREMENTS)

# Run the application
.PHONY: run
run: setup
	PYTHONPATH=. $(VENV_PYTHON) run_wimpyamp.py

# Clean virtual environment
.PHONY: clean
clean:
	rm -rf $(VENV_DIR)

# Install dependencies only
.PHONY: install
install: setup
	$(VENV_PIP) install -r $(REQUIREMENTS)

# Run application directly (assumes environment is set up)
.PHONY: start
start:
	PYTHONPATH=. $(VENV_PYTHON) run_wimpyamp.py

# Code quality checks
.PHONY: lint
lint:
	$(VENV_PIP) install ruff
	$(VENV_PYTHON) -m ruff check .

.PHONY: format-check
format-check:
	$(VENV_PIP) install black
	$(VENV_PYTHON) -m black --check .

.PHONY: format
format:
	$(VENV_PIP) install black
	$(VENV_PYTHON) -m black .

.PHONY: type-check
type-check:
	$(VENV_PIP) install mypy
	$(VENV_PYTHON) -m mypy src/

.PHONY: test
test:
	$(VENV_PIP) install pytest
	$(VENV_PYTHON) -m pytest tests/ -v

.PHONY: check
check: lint format-check type-check

# Help documentation
.PHONY: help
help:
	@echo "Available targets:"
	@echo "  all          - Setup environment and run application (default)"
	@echo "  setup        - Create virtual environment and install dependencies"
	@echo "  run          - Setup environment and run application"
	@echo "  start        - Run application (assumes environment is already set up)"
	@echo "  install      - Install dependencies in existing virtual environment"
	@echo "  clean        - Remove virtual environment"
	@echo "  dist         - Build the application for distribution"
	@echo "  clean-dist   - Remove distribution build artifacts"
	@echo "  dist-archive - Create a final distribution archive (e.g., .dmg)"
	@echo "  bump-patch   - Release a new patch version (e.g., 1.0.0 -> 1.0.1)"
	@echo "  bump-minor   - Release a new minor version (e.g., 1.0.0 -> 1.1.0)"
	@echo "  bump-major   - Release a new major version (e.g., 1.0.0 -> 2.0.0)"
	@echo "  lint         - Run linter (ruff)"
	@echo "  format       - Format code (black)"
	@echo "  format-check - Check code formatting (black --check)"
	@echo "  type-check   - Run type checker (mypy)"
	@echo "  test         - Run tests (pytest)"
	@echo "  check        - Run all quality checks (lint, format, type-check, test)"
	@echo "  help         - Show this help message"

# --- Distribution & Versioning ---

.PHONY: dist
dist:
	@echo "Building application for distribution..."
	$(VENV_PIP) install pyinstaller
	$(VENV_DIR)/bin/pyinstaller WimPyAmp.spec

.PHONY: clean-dist
clean-dist:
	@echo "Cleaning distribution artifacts..."
	rm -rf dist/ build/

.PHONY: dist-archive
dist-archive: dist
	@echo "Creating distribution archive for version $(VERSION)..."
	@if [ "$(shell uname)" = "Darwin" ]; then \
		echo "Performing ad-hoc code signing..."; \
		codesign --force --deep --sign - dist/WimPyAmp.app; \
		echo "Creating DMG archive..."; \
		hdiutil create -srcfolder dist/WimPyAmp.app -volname "WimPyAmp $(VERSION)" dist/WimPyAmp-macOS-$(VERSION).dmg; \
	else \
		echo "Archiving for Windows/Linux is not yet configured."; \
	fi

.PHONY: bump-patch
bump-patch:
	$(VENV_DIR)/bin/bump2version patch

.PHONY: bump-minor
bump-minor:
	$(VENV_DIR)/bin/bump2version minor

.PHONY: bump-major
bump-major:
	$(VENV_DIR)/bin/bump2version major
