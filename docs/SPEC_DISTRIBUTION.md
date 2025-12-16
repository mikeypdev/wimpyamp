# WimPyAmp Distribution Guide

## Overview
This document outlines the steps required to package, bundle, and distribute the WimPyAmp for various platforms. The goal is to create a standalone executable that can run without requiring users to install Python, dependencies, or set up a development environment.

## Target Platforms
- Windows (Windows 7+)
- macOS (10.12+)
- Linux (Ubuntu 18.04+, other distributions with Python 3.11+)

## Distribution Requirements

### Core Requirements
- Self-contained executable with no external dependencies
- Cross-platform compatibility
- Preservation of all original functionality
- Proper handling of skin files (.wsz archives)
- Support for audio files playback
- Maintained window docking and resizing behavior

### Directory Structure for Distribution
```
wimpyamp/
├── wimpyamp.exe (or wimpyamp for macOS/Linux)
├── resources/
│   ├── default_skin/
│   │   └── base-2.91.wsz
│   └── test_skins/
│       └── sample_skin.wsz
├── README.txt
└── licenses/
    ├── python.txt
    ├── pyside.txt
    ├── pillow.txt
    └── other_dependencies.txt
```

## Distribution Packaging

### PyInstaller
**Pros:**
- Mature, well-documented tool
- Good compatibility with PyQt5
- Strong cross-platform support
- Handles binary dependencies well

**Cons:**
- Larger executable size
- May require some configuration for complex dependencies

### Application Icon and Menu Bar Title
- **Menu Bar Title:** On macOS, the title in the menu bar is determined by the application's name. PyInstaller uses the value passed to the `--name` flag for this.
- **Application Icon:** To set a custom icon, you must provide a platform-specific icon file.
    - **macOS:** a `.icns` file.
    - **Windows:** a `.ico` file.
- Create these files and place them in a directory like `resources/icons/`.

**Steps:**
1.  Install PyInstaller in your development environment:
    ```bash
    pip install pyinstaller
    ```

2.  Create a spec file for customized packaging. The `--name` flag sets the application title, and `--icon` sets the icon.
    ```bash
    pyinstaller --onefile --windowed --name "WimPyAmp" --icon "resources/icons/wimpyamp.icns" --add-data "resources:resources" src/ui/main_window.py
    ```

3.  Fine-tune the spec file (`WimPyAmp.spec`) to optimize packaging. A `.spec` file allows for more control, especially for platform-specific settings.

    ```python
    # -*- mode: python ; coding: utf-8 -*-
    import sys

    block_cipher = None

    a = Analysis(
        ['src/ui/main_window.py'],
        pathex=[],
        binaries=[],
        datas=[
            ('resources/default_skin', 'resources/default_skin'),
        ],
        hiddenimports=[],
        hookspath=[],
        hooksconfig={},
        runtime_hooks=[],
        excludes=[],
        win_no_prefer_redirects=False,
        win_private_assemblies=False,
        cipher=block_cipher,
        noarchive=False,
    )

    pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

    exe_options = {
        'name': 'wimpyamp',
        'debug': False,
        'bootloader_ignore_signals': False,
        'strip': False,
        'upx': True,
        'upx_exclude': [],
        'runtime_tmpdir': None,
        'console': False,
        'disable_windowed_traceback': False,
        'argv_emulation': False,
        'target_arch': None,
        'codesign_identity': None,
        'entitlements_file': None,
    }

    # Windows and Linux specific EXE
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        icon='resources/icons/wimpyamp.ico', # Icon for Windows
        **exe_options
    )

    # macOS specific app bundle
    if sys.platform == 'darwin':
        app = BUNDLE(
            exe,
            name='WimPyAmp.app',
            icon='resources/icons/wimpyamp.icns', # Icon for macOS
            bundle_identifier=None # e.g., 'com.yourcompany.wimpyamp'
        )

    ```

4.  Build using the spec file:
    ```bash
    pyinstaller "WimPyAmp.spec"
    ```

## File Organization for Distribution

### Required Files
1. **Main Executable**: The compiled application
2. **Resource Files**: 
   - Default skin (base-2.91.wsz)
3. **Documentation**: 
   - README.txt with installation and usage instructions
   - Licenses for all dependencies
4. **Support Files** (if needed):
   - Configuration files
   - Sample audio files for testing

### Recommended Directory Structure
```
dist/
└── wimpyamp/
    ├── wimpyamp (executable)
    ├── resources/
    │   ├── default_skin/
    │   │   └── base-2.91.wsz
    ├── README.txt
    ├── CHANGELOG.txt
    └── licenses/
        ├── LICENSE.txt
        └── THIRD_PARTY_LICENSES.txt
```

## Pre-Distribution Checklist

### Code Preparation
1. **Remove Development Artifacts**:
   - Remove or disable any debug prints
   - Remove test-specific code
   - Ensure all paths are relative to application directory
   - Test skin loading functionality

2. **Resource Management**:
   - Ensure all required resources are included in the bundle
   - Verify correct path resolution within bundled application
   - Test with default skin and sample skins

3. **Dependencies Check**:
   - Confirm all required dependencies are properly handled
   - Verify audio playback functionality is preserved
   - Test visualization features

### Testing
1. **Cross-Platform Testing**:
   - Test on Windows, macOS, and Linux if targeting all platforms
   - Verify application launches and runs without errors
   - Test all UI interactions and functionality

2. **Performance Testing**:
   - Check startup time of bundled application
   - Verify memory usage is acceptable
   - Test with various skin files

## Creating Distribution Archives

### For Windows
```bash
# Using 7-Zip or similar tool
7z a wimpyamp-windows-x64.zip dist/wimpyamp/
```

### For macOS
```bash
# Create DMG file for better user experience
hdiutil create -srcfolder dist/wimpyamp/ wimpyamp-macos.dmg
```

### For Linux
```bash
# Create tar.gz archive
tar -czf wimpyamp-linux-x64.tar.gz -C dist wimpyamp/
```

## Build Process Automation

### Makefile Integration
Add these targets to your Makefile:

```makefile
# Distribution packaging targets
.PHONY: dist-pyinstaller
dist-pyinstaller:
	pip install pyinstaller
	pyinstaller --onefile --windowed --name "WimPyAmp" --add-data "resources;resources" src/ui/main_window.py

.PHONY: dist-all
dist-all: dist-pyinstaller
	@echo "Distribution created in dist/ directory"

.PHONY: clean-dist
clean-dist:
	rm -rf dist/ build/ *.spec
```

### CI/CD Pipeline Considerations
- Set up separate build jobs for each target platform
- Use platform-specific Docker images for consistent builds
- Sign executables for distribution on Windows/macOS
  - **macOS**: Requires Apple Developer Program membership ($99/year) for proper code signing and notarization
  - **Windows**: Certificate from a trusted CA (e.g., DigiCert, Sectigo) for authenticode signing
  - **Linux**: Usually no code signing required
- For development/testing only, ad-hoc code signing can be used without official certificates
- Automate testing of bundled application
- Generate checksums for distribution files

## Post-Distribution Verification

### Verification Checklist
- [ ] Application launches without errors
- [ ] Default skin loads correctly
- [ ] All UI elements respond properly
- [ ] Skin loading functionality works
- [ ] Audio playback features work
- [ ] Visualization features work
- [ ] Window docking behavior preserved
- [ ] All buttons and controls function
- [ ] Help/about dialogs display correctly

### Common Issues and Solutions
1. **Missing Resources**: Ensure all resource files are properly included in the bundle
2. **Dependency Errors**: Verify all required Python packages are included
3. **Path Issues**: Use relative paths and `sys._MEIPASS` for bundled resources
4. **Audio Issues**: Confirm audio libraries are properly bundled

## Release Strategy

### Versioning
- Use semantic versioning (v1.0.0 format)
- Include release notes with each version
- Tag releases in source control

### Distribution Channels
- GitHub Releases for open source distribution
- Personal website or project page
- Platform-specific application stores (if applicable)

## Maintenance Considerations

### Updating Dependencies
- Regular security updates for dependencies
- Periodic testing with new Python versions
- Compatibility verification with new OS releases

### User Support
- Provide clear installation instructions
- Document known issues and workarounds
- Offer support channels for users
- Collect feedback for future improvements
