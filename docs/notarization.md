# macOS Notarization Guide

This guide explains how to build, sign, and notarize WimPyAmp for macOS distribution outside the App Store.

## Overview

Apple requires code signing and notarization for macOS apps distributed outside the App Store. Without these, users will see Gatekeeper warnings when launching the app.

The build process supports three modes:

1. **Unsigned** - Development builds (fast, no credentials required)
2. **Signed** - Ad-hoc distribution (requires Developer ID, skips notarization)
3. **Signed + Notarized** - Production releases (requires Developer ID + Apple credentials)

## Prerequisites

### 1. Apple Developer Account

You need an active [Apple Developer Program](https://developer.apple.com/programs/) membership.

### 2. Developer ID Certificate

Install a "Developer ID Application" certificate from Xcode:

```bash
# Download and install via Xcode
open "https://developer.apple.com/account/resources/certificates/list"
```

Or create one via command line:
```bash
# Requires Xcode Command Line Tools
security find-identity -v -p codesigning | grep "Developer ID Application"
```

### 3. Apple Credentials

Choose one of two authentication methods:

#### Option A: App-Specific Passwords (Recommended for Individuals)
- Go to [appleid.apple.com](https://appleid.apple.com)
- Sign in and navigate to Security → App-Specific Passwords
- Generate a new password with label "WimPyAmp Notarization"
- Use this password as `APPLE_ID_PASSWORD`

#### Option B: App Store Connect API (Recommended for Teams)
- Go to [App Store Connect](https://appstoreconnect.apple.com)
- Navigate to Users and Access → Keys
- Create a new API key with "Developer" role
- Note down:
  - Key ID
  - Issuer ID
  - Download the `.p8` private key file
- Use `xcrun notarytool store-credentials` to save credentials:
  ```bash
  xcrun notarytool store-credentials "notarytool-profile" \
    --apple-id YOUR_APPLE_ID \
    --password APP_SPECIFIC_PASSWORD \
    --team-id YOUR_TEAM_ID
  ```

## Configuration

### Create `.env` File

Create a `.env` file in the project root (already gitignored):

```bash
# Code signing
APPLE_SIGNING_IDENTITY="Developer ID Application: Your Name (XXXXXXXXXX)"

# Notarization credentials (app-specific password method)
APPLE_ID="your.email@example.com"
APPLE_ID_PASSWORD="xxxx-xxxx-xxxx-xxxx"
APPLE_TEAM_ID="XXXXXXXXXX"
```

**Note:** The `APPLE_TEAM_ID` is the 10-character Team ID from your Apple Developer account.

### Find Your Credentials

```bash
# List all signing certificates
security find-identity -v -p codesigning

# Find your Team ID
grep -A 5 "TeamIdentifier" ~/Library/MobileDevice/Provisioning\ Profiles/*.mobileprovision
```

## Build Modes

### Mode 1: Unsigned (Development)

Fast builds with no signing. For local testing only.

```bash
make dist-archive
```

**Result:** Unsigned `.app` and `.dmg`
**Gatekeeper:** Will show "unidentified developer" warning
**Use case:** Quick development iterations

### Mode 2: Signed (Ad-Hoc Distribution)

Signs the app but doesn't notarize. For trusted distribution.

```bash
# Ensure .env has APPLE_SIGNING_IDENTITY
make dist-archive
```

**Result:** Signed `.app` and `.dmg` without notarization ticket
**Gatekeeper:** May still warn on fresh downloads
**Use case:** Beta testing with trusted users

### Mode 3: Signed + Notarized (Production)

Full signing and notarization. For public releases.

```bash
# Ensure .env has all credentials
make dist-notarize
```

**Result:** Signed and notarized `.dmg` with stapled ticket
**Gatekeeper:** No warnings, instant launch
**Use case:** Public releases on GitHub

**Important:** Running `make dist-archive` or `make dist-notarize` multiple times with the same version will **replace** the existing archive. To keep multiple builds, use `make bump-patch` to increment the version before building again.

## Commands

### Build and Notarize
```bash
make dist-notarize
```

This builds, signs, notarizes, and verifies the app in one command.

### Check Notarization Status
```bash
make verify-notarization
```

Shows recent notarization submissions and their status.

### Manual Verification
```bash
# Check signature
codesign --verify --deep --verbose=2 dist/WimPyAmp.app

# Check Gatekeeper acceptance
spctl --assess --verbose --type execute dist/WimPyAmp.app

# Validate stapled ticket
xcrun stapler validate dist/WimPyAmp-macOS-arm64-vX.X.X.dmg
```

### Clean Build Artifacts
```bash
# Remove all build outputs (app bundles, archives)
make clean-dist

# Remove archives only (keeps app bundle)
rm -f dist/*.dmg dist/*.zip dist/*.tar.gz
```

## Troubleshooting

### "No suitable application records were found"

**Cause:** Team ID mismatch or incorrect Apple credentials.

**Solution:**
```bash
# Verify Team ID matches your developer account
xcrun notarytool history --limit 1 --apple-id "$APPLE_ID" --password "$APPLE_ID_PASSWORD" --team-id "$APPLE_TEAM_ID"
```

### "The software has been altered"

**Cause:** File changed after signing (e.g., `.DS_Store` files, extended attributes).

**Solution:**
```bash
# Remove extended attributes before signing
xattr -cr dist/WimPyAmp.app

# Re-sign
make dist-notarize
```

### Notarization Timeout

**Cause:** Apple's notarization service can be slow (2-15 minutes typical).

**Solution:** The `--wait` flag handles this automatically. Check status with `make verify-notarization`.

### Codesign Fails on Binaries

**Cause:** PyInstaller creates unsigned binaries that need individual signing.

**Solution:** The Makefile already handles this with:
```bash
find dist/WimPyAmp.app/Contents/Frameworks -type f \( -name "*.dylib" -or -name "*.so" \) -print0 | xargs -0 codesign --force --verify --verbose --timestamp --options runtime --sign "$(APPLE_SIGNING_IDENTITY)"
```

### Entitlements Issues

**Current entitlements** (`macos.entitlements`):
- `com.apple.security.cs.allow-unsigned-executable-memory` - Required for Python JIT
- `com.apple.security.cs.disable-library-validation` - Required for PyInstaller's dynamic loading

**Warning:** These are broad entitlements. Apple may request justification during notarization review.

### Gatekeeper Still Warns After Notarization

**Cause:** Quarantine flag from web download.

**Solution:** Users must:
```bash
xattr -cr ~/Downloads/WimPyAmp-macOS-arm64-vX.X.X.dmg
```

Or double-click to mount the DMG before opening.

## GitHub Actions Integration

The CI workflow automatically creates signed and notarized macOS builds for tagged releases.

### How It Works

| Trigger | macOS Build | Signing | Notarization |
|---------|-------------|---------|--------------|
| Push to main | ✅ Checks only | ❌ No | ❌ No |
| Pull request | ✅ Checks only | ❌ No | ❌ No |
| Tagged release | ✅ Builds | ✅ Signed | ✅ Yes |

**Key benefits:**
- CI builds stay fast (no notarization overhead)
- PRs can be tested without Apple credentials
- Tagged releases are automatically signed and notarized
- Draft releases are created automatically

### 1. Add Secrets to GitHub Repository

Go to **Settings → Secrets and variables → Actions** and add:
- `APPLE_SIGNING_IDENTITY` - Your Developer ID (e.g., "Developer ID Application: Your Name (XXXXXXXXXX)")
- `APPLE_ID` - Your Apple ID email
- `APPLE_ID_PASSWORD` - App-specific password
- `APPLE_TEAM_ID` - Your 10-character Team ID

### 2. Workflow Structure

The `.github/workflows/ci.yml` already has this configuration:

```yaml
# Non-tag builds run checks only; archives are created on tagged releases
# Tagged releases - full signing and notarization
- name: Import Code Signing Certificate
  if: startsWith(github.ref, 'refs/tags/v') && (matrix.os == 'macos-latest' || matrix.os == 'macos-15-intel')
  run: |
    KEYCHAIN_PATH="/Users/runner/work/_temp/app-signing.keychain-db"
    security create-keychain -p "" $KEYCHAIN_PATH
    security set-keychain-settings -lut 21600 $KEYCHAIN_PATH
    security unlock-keychain -p "" $KEYCHAIN_PATH
    echo "$APPLE_SIGNING_CERTIFICATE_P12_BASE64" | base64 --decode -o certificate.p12
    security import certificate.p12 -P "$APPLE_SIGNING_CERTIFICATE_PASSWORD" -A -t cert -f pkcs12 -k $KEYCHAIN_PATH
    security default-keychain -d user -s $KEYCHAIN_PATH
    security find-identity -v -p codesigning

- name: Create signed and notarized distribution (tags only)
  if: startsWith(github.ref, 'refs/tags/v') && (matrix.os == 'macos-latest' || matrix.os == 'macos-15-intel')
  run: |
    make setup
    ARCH=${{ matrix.arch }} make dist-archive NOTARIZE=true
  env:
    APPLE_SIGNING_IDENTITY: ${{ secrets.APPLE_SIGNING_IDENTITY }}
    APPLE_ID: ${{ secrets.APPLE_ID }}
    APPLE_ID_PASSWORD: ${{ secrets.APPLE_ID_PASSWORD }}
    APPLE_TEAM_ID: ${{ secrets.APPLE_TEAM_ID }}

# Tagged releases - full signing and notarization
- name: Import Code Signing Certificate
  if: startsWith(github.ref, 'refs/tags/v') && (matrix.os == 'macos-latest' || matrix.os == 'macos-15-intel')
  run: |
    KEYCHAIN_PATH="/Users/runner/work/_temp/app-signing.keychain-db"
    security create-keychain -p "" $KEYCHAIN_PATH
    security set-keychain-settings -lut 21600 $KEYCHAIN_PATH
    security unlock-keychain -p "" $KEYCHAIN_PATH
    echo "$APPLE_SIGNING_CERTIFICATE_P12_BASE64" | base64 --decode -o certificate.p12
    security import certificate.p12 -P "$APPLE_SIGNING_CERTIFICATE_PASSWORD" -A -t cert -f pkcs12 -k $KEYCHAIN_PATH
    security default-keychain -d user -s $KEYCHAIN_PATH
    security find-identity -v -p codesigning

- name: Create signed and notarized distribution (tags only)
  if: startsWith(github.ref, 'refs/tags/v') && (matrix.os == 'macos-latest' || matrix.os == 'macos-15-intel')
  run: |
    make setup
    ARCH=${{ matrix.arch }} make dist-archive NOTARIZE=true
  env:
    APPLE_SIGNING_IDENTITY: ${{ secrets.APPLE_SIGNING_IDENTITY }}
    APPLE_ID: ${{ secrets.APPLE_ID }}
    APPLE_ID_PASSWORD: ${{ secrets.APPLE_ID_PASSWORD }}
    APPLE_TEAM_ID: ${{ secrets.APPLE_TEAM_ID }}
```

### 3. Create Tagged Release

```bash
# Bump version
make bump-minor

# Push tags
make push-tags

# GitHub Actions will automatically:
# 1. Build for all platforms
# 2. Sign and notarize macOS builds
# 3. Create a draft release with all artifacts
```

## Best Practices

1. **Always verify locally first:** Test `make dist-notarize` locally before automating
2. **Keep credentials secure:** Never commit `.env` or add secrets to GitHub
3. **Version consistency:** Tag releases with semantic versioning (`v1.2.3`)
4. **Test on clean Mac:** Download the DMG from a "fresh" Mac to verify Gatekeeper behavior
5. **Monitor notarization history:** Use `make verify-notarization` to spot patterns in failures
6. **Keep entitlements minimal:** Only request permissions your app actually needs

## Additional Resources

- [Apple Notarization Documentation](https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution)
- [Xcrun Notarytool](https://developer.apple.com/documentation/xcode/notarizing_macos_software_before_distribution/customizing_the_notarization_workflow)
- [Code Signing Guide](https://developer.apple.com/library/archive/documentation/Security/Conceptual/CodeSigningGuide/Introduction/Introduction.html)
- [Gatekeeper User Guide](https://support.apple.com/en-us/guide/secure-boot/welcome/web)

## Summary

| Mode | Credentials | Gatekeeper | Use Case |
|------|-------------|------------|----------|
| Unsigned | None | Warning | Development |
| Signed | Cert only | May warn | Beta testing |
| Signed+Notarized | Cert + Apple ID | No warning | Production releases |

**Quick start for production:**
```bash
# 1. Setup .env with credentials
# 2. Build and notarize
make dist-notarize

# 3. Verify
make verify-notarization

# 4. Test DMG on clean Mac
# 5. Upload to GitHub release
```
