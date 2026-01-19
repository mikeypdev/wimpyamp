# -*- mode: python ; coding: utf-8 -*-

# Read the version from the VERSION file
import os
# Use relative path from the current working directory where the spec file is located
version_file_path = 'VERSION'  # PyInstaller should look in the same directory as the spec file
with open(version_file_path, 'r') as f:
    app_version = f.read().strip()

a = Analysis(
    ['run_wimpyamp.py'],
    pathex=[],
    binaries=[],
    datas=[('resources', 'resources'), ('VERSION', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='WimPyAmp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,  # Set to your Developer ID if available, e.g., "Developer ID Application: Your Name (XXXXXXXXXX)"
    entitlements_file=None,  # Path to entitlements file if needed for specific macOS permissions/features
    icon='resources/icons/wimpyamp.ico',  # Icon for Windows and Linux
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='WimPyAmp',
)
app = BUNDLE(
    coll,
    name='WimPyAmp.app',
    icon='resources/icons/wimpyamp.icns',
    bundle_identifier=None,
    info_plist={
        'CFBundleShortVersionString': app_version,
        'CFBundleVersion': app_version,
        'CFBundleDocumentTypes': [
            {
                'CFBundleTypeName': 'Audio Files',
                'CFBundleTypeExtensions': ['mp3', 'wav', 'ogg', 'flac', 'm4a', 'aac', 'opus', 'aiff', 'au'],
                'CFBundleTypeIconFile': 'wimpyamp.icns',
                'LSItemContentTypes': ['public.audio'],
                'LSHandlerRank': 'Owner'
            },
            {
                'CFBundleTypeName': 'Playlist Files',
                'CFBundleTypeExtensions': ['m3u', 'm3u8', 'pls', 'txt'],
                'CFBundleTypeIconFile': 'wimpyamp.icns',
                'LSItemContentTypes': ['public.plain-text'],
                'LSHandlerRank': 'Owner'
            }
        ],
        'CFBundleURLTypes': [
            {
                'CFBundleURLName': 'com.wimpyamp.audio',
                'CFBundleURLSchemes': ['wimpyamp']
            }
        ],
        'NSAppleEventsUsageDescription': 'WimPyAmp can respond to Apple Events for file and directory opening.',
    }
)
