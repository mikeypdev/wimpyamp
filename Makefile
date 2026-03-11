# Makefile for WimPyAmp

# OS detection and path configuration
OS_NAME := $(shell uname -s)
DETECTED_ARCH := $(shell uname -m)
ARCH ?= $(DETECTED_ARCH)

ifeq ($(OS),Windows_NT)
    # Windows-specific settings (works with Git Bash/MSYS make)
    VENV_BIN_DIR := Scripts
    PYTHON := python
    VENV_DIR := venv
    VENV_PYTHON := $(VENV_DIR)/$(VENV_BIN_DIR)/python.exe
    VENV_PIP := $(VENV_DIR)/$(VENV_BIN_DIR)/pip.exe
    IS_WINDOWS := 1
else
    # Unix-like settings (Linux, macOS)
    VENV_BIN_DIR := bin
    PYTHON := python3
    VENV_DIR := venv
    VENV_PYTHON := $(VENV_DIR)/$(VENV_BIN_DIR)/python
    VENV_PIP := $(VENV_DIR)/$(VENV_BIN_DIR)/pip
    IS_WINDOWS := 0
endif

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
	@echo "  bump-patch   - Release a new patch version"
	@echo "  bump-minor   - Release a new minor version"
	@echo "  bump-major   - Release a new major version"
	@echo "  lint         - Run linter (ruff)"
	@echo "  format       - Format code (black)"
	@echo "  format-check - Check code formatting (black --check)"
	@echo "  type-check   - Run type checker (mypy)"
	@echo "  test         - Run tests (pytest)"
	@echo "  check        - Run all quality checks (lint, format, type-check, test)"
	@echo "  website-serve - Start local web server for website preview"
	@echo "  website-deploy - Show deployment instructions"
	@echo "  help         - Show this help message"

# --- Distribution & Versioning ---

.PHONY: dist
dist:
	@echo "Building application for distribution..."
	$(VENV_PIP) install pyinstaller
	$(VENV_PYTHON) -m PyInstaller WimPyAmp.spec

.PHONY: clean-dist
clean-dist:
	@echo "Cleaning distribution artifacts..."
	rm -rf dist/ build/

.PHONY: dist-archive
dist-archive: dist
	@echo "Creating distribution archive for version $(VERSION) on $(OS_NAME) ($(ARCH))..."
	@if [ "$(OS_NAME)" = "Darwin" ]; then \
		echo "Performing ad-hoc code signing..."; \
		codesign --force --deep --sign - dist/WimPyAmp.app; \
		echo "Creating DMG archive..."; \
		hdiutil create -srcfolder dist/WimPyAmp.app -volname "WimPyAmp $(VERSION)" dist/WimPyAmp-macOS-$(ARCH)-v$(VERSION).dmg; \
	elif [ "$(IS_WINDOWS)" = "1" ]; then \
		echo "Creating ZIP archive for Windows..."; \
		powershell -Command "Compress-Archive -Path dist/WimPyAmp -DestinationPath dist/WimPyAmp-Windows-$(ARCH)-v$(VERSION).zip -Force"; \
	elif [ "$(OS_NAME)" = "Linux" ]; then \
		echo "Creating tarball for Linux..."; \
		cd dist && tar -czf WimPyAmp-Linux-$(ARCH)-v$(VERSION).tar.gz WimPyAmp; \
	else \
		echo "Archiving for unknown OS: $(OS_NAME)"; \
	fi

.PHONY: bump-patch
bump-patch:
	$(VENV_PYTHON) -m bumpversion patch

.PHONY: bump-minor
bump-minor:
	$(VENV_PYTHON) -m bumpversion minor

.PHONY: bump-major
bump-major:
	$(VENV_PYTHON) -m bumpversion major

.PHONY: push-tags
push-tags:
	git push && git push --tags

.PHONY: release-patch
release-patch: bump-patch push-tags

.PHONY: release-minor
release-minor: bump-minor push-tags

.PHONY: release-major
release-major: bump-major push-tags

# --- Website ---

.PHONY: website-serve
website-serve:
	@echo "Starting local server at http://localhost:8000"
	@echo "Press Ctrl+C to stop"
	cd website && $(PYTHON) -m http.server 8000

.PHONY: website-deploy
website-deploy:
	@echo "Push to main branch to trigger automatic deployment"
	@echo "GitHub Actions will deploy to gh-pages"
