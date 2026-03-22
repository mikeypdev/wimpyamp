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

# Load Apple credentials from .env if it exists
ifneq ($(wildcard .env),)
    # Use include and strip quotes to ensure variables are usable in both make and shell
    include .env
    export
endif

# Ensure these variables don't have literal quotes from .env
APPLE_SIGNING_IDENTITY := $(subst ",,$(APPLE_SIGNING_IDENTITY))
APPLE_ID := $(subst ",,$(APPLE_ID))
APPLE_ID_PASSWORD := $(subst ",,$(APPLE_ID_PASSWORD))
APPLE_TEAM_ID := $(subst ",,$(APPLE_TEAM_ID))

# Default notarization state (can be overridden by command line)
NOTARIZE ?= false

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
check: lint format-check type-check test

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
	@echo "  dist-archive - Create a final distribution archive (replaces existing)"
	@echo "  dist-notarize- Build, sign, and notarize macOS distribution"
	@echo "  verify-notarization - Check recent notarization submissions status"
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
	$(VENV_PYTHON) -m PyInstaller --noconfirm WimPyAmp.spec

.PHONY: clean-dist
clean-dist:
	@echo "Cleaning distribution artifacts..."
	rm -rf dist/ build/

.PHONY: dist-archive
dist-archive: dist
	@echo "Creating distribution archive for version $(VERSION) on $(OS_NAME) ($(ARCH))..."
	@if [ "$(OS_NAME)" = "Darwin" ]; then \
		echo "Cleaning old archives..."; \
		rm -f dist/WimPyAmp-macOS-$(ARCH)-v$(VERSION).dmg; \
		echo "Repairing bundle permissions..."; \
		xattr -cr dist/WimPyAmp.app || true; \
		if [ "$(NOTARIZE)" = "true" ]; then \
			if [ -z "$(APPLE_SIGNING_IDENTITY)" ]; then \
				echo "Error: APPLE_SIGNING_IDENTITY not set in .env"; \
				exit 1; \
			fi; \
			if [ -z "$(APPLE_ID)" ] || [ -z "$(APPLE_ID_PASSWORD)" ] || [ -z "$(APPLE_TEAM_ID)" ]; then \
				echo "Error: Missing notarization credentials (APPLE_ID, APPLE_ID_PASSWORD, or APPLE_TEAM_ID) in .env"; \
				exit 1; \
			fi; \
			echo "Signing app with Hardened Runtime using identity: $(APPLE_SIGNING_IDENTITY)"; \
			find dist/WimPyAmp.app/Contents/Frameworks -type f \( -name "*.dylib" -or -name "*.so" -or -name "WimPyAmp" -or -not -name "*.*" \) -not -path "*/_CodeSignature/*" -print0 | xargs -0 codesign --force --verify --verbose --timestamp --options runtime --sign "$(APPLE_SIGNING_IDENTITY)"; \
			find dist/WimPyAmp.app/Contents/Frameworks -type d -name "*.framework" -print0 | xargs -0 codesign --force --verify --verbose --timestamp --options runtime --sign "$(APPLE_SIGNING_IDENTITY)"; \
			find dist/WimPyAmp.app/Contents/MacOS -type f -print0 | xargs -0 codesign --force --verify --verbose --timestamp --options runtime --entitlements macos.entitlements --sign "$(APPLE_SIGNING_IDENTITY)"; \
			echo "Performing final deep-sign on app bundle..."; \
			codesign --force --verify --verbose --deep --options runtime --timestamp --entitlements macos.entitlements --sign "$(APPLE_SIGNING_IDENTITY)" dist/WimPyAmp.app; \
			echo "Verifying local signature and Gatekeeper compliance..."; \
			codesign --verify --deep --verbose=2 dist/WimPyAmp.app; \
			echo "Note: spctl --assess will fail until app is notarized."; \
			spctl --assess --verbose --type execute dist/WimPyAmp.app || true; \
		else \
			echo "Performing ad-hoc code signing..."; \
			codesign --force --deep --sign - dist/WimPyAmp.app; \
		fi; \
		echo "Creating DMG archive..."; \
		hdiutil create -quiet -srcfolder dist/WimPyAmp.app -volname "WimPyAmp $(VERSION)" dist/WimPyAmp-macOS-$(ARCH)-v$(VERSION).dmg; \
		if [ "$(NOTARIZE)" = "true" ]; then \
			echo "Signing and submitting DMG..."; \
			codesign --force --verify --verbose --timestamp --sign "$(APPLE_SIGNING_IDENTITY)" dist/WimPyAmp-macOS-$(ARCH)-v$(VERSION).dmg; \
			xcrun notarytool submit "dist/WimPyAmp-macOS-$(ARCH)-v$(VERSION).dmg" --apple-id "$(APPLE_ID)" --password "$(APPLE_ID_PASSWORD)" --team-id "$(APPLE_TEAM_ID)" --no-progress --wait --timeout 20m; \
			echo "Stapling ticket..."; \
			xcrun stapler staple "dist/WimPyAmp-macOS-$(ARCH)-v$(VERSION).dmg"; \
			echo "Verifying stapled ticket..."; \
			xcrun stapler validate "dist/WimPyAmp-macOS-$(ARCH)-v$(VERSION).dmg"; \
			echo "Verifying Gatekeeper acceptance..."; \
			spctl --assess --verbose --type execute "dist/WimPyAmp-macOS-$(ARCH)-v$(VERSION).dmg"; \
			echo "Notarization complete!"; \
		fi; \
	elif [ "$(IS_WINDOWS)" = "1" ]; then \
		echo "Cleaning old archives..."; \
		rm -f dist/WimPyAmp-Windows-$(ARCH)-v$(VERSION).zip; \
		echo "Creating ZIP archive for Windows..."; \
		powershell -Command "Compress-Archive -Path dist/WimPyAmp -DestinationPath dist/WimPyAmp-Windows-$(ARCH)-v$(VERSION).zip -Force"; \
	elif [ "$(OS_NAME)" = "Linux" ]; then \
		echo "Cleaning old archives..."; \
		rm -f dist/WimPyAmp-Linux-$(ARCH)-v$(VERSION).tar.gz; \
		echo "Creating tarball for Linux..."; \
		cd dist && tar -czf WimPyAmp-Linux-$(ARCH)-v$(VERSION).tar.gz WimPyAmp; \
	else \
		echo "Archiving for unknown OS: $(OS_NAME)"; \
	fi

.PHONY: dist-notarize
dist-notarize:
	@echo "Building, signing, and notarizing macOS distribution..."
	$(MAKE) dist-archive NOTARIZE=true

.PHONY: verify-notarization
verify-notarization:
	@echo "Checking recent notarization submissions..."
	@if [ -z "$(APPLE_ID)" ] || [ -z "$(APPLE_ID_PASSWORD)" ] || [ -z "$(APPLE_TEAM_ID)" ]; then \
		echo "Error: Missing notarization credentials (APPLE_ID, APPLE_ID_PASSWORD, or APPLE_TEAM_ID) in .env"; \
		exit 1; \
	fi
	xcrun notarytool history --limit 10 --apple-id "$(APPLE_ID)" --password "$(APPLE_ID_PASSWORD)" --team-id "$(APPLE_TEAM_ID)"


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
