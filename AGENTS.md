# AGENTS.md

## Agent Configuration

This project uses lightweight agent operational directives.

**READ FIRST: [AGENT-lite.md](./AGENT-lite.md)**
@./AGENT-lite.md

All agent interactions must follow the protocols defined in AGENT-lite.md, including:
- No autonomous decisions
- Inherent limitations
- Operational process
- Token economy guideline
- Human interaction protocol

**Agent Runtime Monitoring:**
When running the application, agents should monitor the console or debug output for any errors or warnings. If issues are detected in the output, the agent should offer to fix them proactively.

---

# Project: WimPyAmp

## Project Overview
WimPyAmp is a cross-platform desktop music player.
It renders classic Winamp skins with pixel-perfect accuracy and uses them for the music player UI.

## Main Technologies
* **Primary Language:** Python 3.13+
* **GUI Framework:** PySide6 (for rapid development and cross-platform compatibility)
* **Image Processing:** Pillow (for advanced image manipulation and handling various BMP formats)
* **Audio Libraries:** mutagen (metadata), librosa (analysis), sounddevice (playback), scipy and numpy (audio processing)
* **Archive Handling:** Python's built-in `zipfile` module (for `.wsz` file extraction)

## Current Architecture
The project is structured into logical components to manage skin parsing, sprite rendering, and UI interactions:
*   **`src/core/`**: Contains the core logic for `skin_parser.py` (handling `.wsz` extraction and parsing), `sprite_manager.py` (caching and managing sprites), `renderer.py` (the main rendering engine), `skin_data.py` (data structures), `region_parser.py` (region definitions), and `user_preferences.py` (user settings).
*   **`src/ui/`**: Implements the graphical user interface, including `main_window.py`, `playlist_window.py`, `equalizer_window.py`, `album_art_window.py`, and various playlist-related components (`playlist_buttonbar.py`, `playlist_config.py`, `playlist_constants.py`, `playlist_menu.py`, `playlist_scrollbar.py`), along with `ui_state.py`.
*   **`src/utils/`**: Provides utility functions such as `color.py` (for color and palette handling), `geometry.py` (for coordinate calculations), `text_renderer.py` (for drawing text), `scrolling_text_renderer.py`, `region_utils.py`, and `sprite_validator.py`.
*   **`resources/`**: Stores assets like `default_skin/`, `default_art/`, `icons/`, and `specs/` for skin specifications.
*   **`tests/`**: Dedicated directory for unit tests covering core functionalities.
*   **`test_data/`**: Directory containing test skin files and audio samples.

## Building and Running
To set up and run the project, you can use the provided Makefile which standardizes the setup and execution process across different environments.

**1. Setup and Run:**

```bash
make
```

This will create a virtual environment, install dependencies, and launch the application.

**Alternative Makefile targets:**

```bash
make setup        # Create virtual environment and install dependencies
make run          # Setup environment and run application
make start        # Run application (assumes environment is already set up)
make clean        # Remove virtual environment
make test         # Run tests with pytest
make lint         # Run linter (ruff)
make format       # Format code (black)
make type-check   # Run type checker (mypy)
make check        # Run all quality checks (lint, format, type-check, test)
make dist         # Build application for distribution
```

The application's main window, displaying the default Winamp skin, should appear on the screen after running the application.

## Development Conventions
*   **Language Version:** Python 3.13 or newer.
*   **Dependency Management:** Use `venv` and `requirements.txt` to manage project dependencies.
*   **Code Style:** Adhere to standard Python best practices (e.g., PEP 8) with Black formatting and Ruff linting.
*   **Testing:** Unit tests are crucial, especially for `skin_parser`, `renderer`, and interaction logic.
*   **Documentation:** Refer to the `docs/` directory for comprehensive specifications, including `winamp_skin_spec.json` for detailed sprite coordinates and rendering rules, and various RTF/PDF documents for the authoritative skin format specification.
*   **Image Handling:** The application must correctly handle BMP images (1/4/8/24-bit), preserve indexed color palettes, and implement transparency based on key color detection (magenta `#FF00FF`, top-left pixel, or `skin.ini` specified index). Images should be converted to 32-bit RGBA for composition.
*   **Sprite Extraction:** Pixel-perfect coordinate extraction and handling of sprite states (normal, pressed) and z-order for overlapping elements are critical.
*   **High-DPI Support:** The rendering pipeline should account for high-DPI displays and device pixel ratio scaling.
*   **Version Management:** The project uses semantic versioning with bump2version for version management.

