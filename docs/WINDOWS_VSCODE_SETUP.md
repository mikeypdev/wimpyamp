# Windows 11 — VS Code + venv Setup (Windows helper scripts + VS Code)

This file shows how to set up and run WimPyAmp on Windows 11 using a local virtual environment and the helper scripts and VS Code task/launch files included in the repository.

Quick manual setup (PowerShell):

```powershell
python -m venv venv
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
venv\Scripts\python -m pip install --upgrade pip
venv\Scripts\python -m pip install -r requirements.txt
$env:PYTHONPATH='.'; venv\Scripts\python run_wimpyamp.py
```

Quick manual setup (cmd.exe):

```cmd
python -m venv venv
venv\Scripts\python -m pip install --upgrade pip
venv\Scripts\python -m pip install -r requirements.txt
set PYTHONPATH=. && venv\Scripts\python run_wimpyamp.py
```

Use the provided helper scripts and VS Code tasks (recommended)

The repository includes Windows helper scripts in `winscripts/` and VS Code task/launch files in `.vscode/` so contributors can run common workflows without remembering platform-specific commands.

Run setup (create venv and install dependencies) from PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\winscripts\setup.ps1
```

Start the application (sets `PYTHONPATH` automatically):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\winscripts\run.ps1
```

Or use VS Code tasks: Command Palette → `Tasks: Run Task` → choose `Setup (winscripts)` or `Run WimPyAmp`.

VS Code notes

- Interpreter: choose the workspace venv via `Python: Select Interpreter` (recommended path: `${workspaceFolder}\\venv\\Scripts\\python.exe`). Avoid committing machine-specific interpreter paths in `.vscode/settings.json`.
- Debug: use the `.vscode/launch.json` configuration named "Run WimPyAmp (venv)" (Run view / F5).
- Tasks: run `.vscode/tasks.json` entries: `Setup (winscripts)`, `Run WimPyAmp`, `Lint (ruff)`, `Test (pytest)`.
- Extensions: install recommended extensions from `.vscode/extensions.json` (we recommend `ms-python.python`, `ms-python.vscode-pylance`, and `ms-python.black-formatter`).

Makefile target equivalents (PowerShell)

```powershell
# setup
python -m venv venv
venv\Scripts\python -m pip install --upgrade pip
venv\Scripts\python -m pip install -r requirements.txt

# run / start
$env:PYTHONPATH='.'; venv\Scripts\python run_wimpyamp.py

# install (dependencies only)
venv\Scripts\python -m pip install -r requirements.txt

# clean
Remove-Item -Recurse -Force venv

# lint
venv\Scripts\python -m pip install ruff
venv\Scripts\python -m ruff check .

# format-check
venv\Scripts\python -m pip install black
venv\Scripts\python -m black --check .

# format
venv\Scripts\python -m black .

# type-check
venv\Scripts\python -m pip install mypy
venv\Scripts\python -m mypy src/

# test
venv\Scripts\python -m pip install pytest
venv\Scripts\python -m pytest tests/ -v

# dist (pyinstaller)
venv\Scripts\python -m pip install pyinstaller
venv\Scripts\pyinstaller WimPyAmp.spec

# Windows helper script: `winscripts/dist.ps1`
The repository includes a Windows packaging helper script `winscripts/dist.ps1` that
invokes PyInstaller using the project venv and the existing `WimPyAmp.spec`, then
collects the build artifacts and creates a dated ZIP in `dist/`.

Run it from PowerShell (recommended):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\winscripts\dist.ps1
```

Optional parameters:
- `-VenvPath` : path to the virtual environment (default `.
venv`)
- `-SpecFile` : spec file to use (default `WimPyAmp.spec`)
- `-DistDir`  : output directory for collected artifacts (default `.
dist`)

The script will install PyInstaller into the venv if it's missing, run the spec-based
build, then create an archive like `dist\wimpyamp-YYYYMMDD.zip`.

# bump version (bump2version inside venv)
venv\Scripts\bump2version patch
venv\Scripts\bump2version minor
venv\Scripts\bump2version major
```

Notes

- The Makefile contains macOS-specific packaging steps (codesign/hdiutil). On Windows, a `pyinstaller` build plus zipping (`Compress-Archive`) is a practical alternative.
- If you prefer to use the Makefile unchanged, run it under WSL where the Unix paths (`venv/bin/...`) match the Makefile.
- Commit `.vscode/launch.json`, `.vscode/tasks.json`, and `.vscode/extensions.json` to share developer workflows; keep `.vscode/settings.json` portable.
