# Semantic Versioning Guide for Buildbotics CNC Controller

This document describes the semantic versioning system implemented for the Buildbotics CNC Controller firmware, following SemVer specification with custom pre-release identifiers.

## Overview

The Buildbotics CNC Controller now uses **Semantic Versioning (SemVer)** with support for pre-release versions and build metadata. This provides clear communication about the nature of changes and the stability of releases.

## Version Format

```
MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]
```

### Components

- **MAJOR**: Breaking changes that are not backward compatible
- **MINOR**: New features that are backward compatible
- **PATCH**: Bug fixes that are backward compatible
- **PRERELEASE** (optional): Pre-release identifier (dev, alpha, beta, rc)
- **BUILD** (optional): Build metadata (e.g., build.123)

## Pre-release Identifiers

The system uses custom pre-release identifiers that follow the development workflow:

| Identifier | Description | Example |
|------------|-------------|---------|
| `dev` | Development releases | `2.2.0-dev.1` |
| `alpha` | Alpha testing releases | `2.2.0-alpha.1` |
| `beta` | Beta testing releases | `2.2.0-beta.1` |
| `rc` | Release candidate | `2.2.0-rc.1` |

## Development Workflow

### Version Progression

```
2.2.0-dev.1 → 2.2.0-dev.2 → ... → 2.2.0-dev.n
    ↓ (development ready)
2.2.0-alpha.1 → 2.2.0-alpha.2 → ... → 2.2.0-alpha.n
    ↓ (initial testing ready)
2.2.0-beta.1 → 2.2.0-beta.2 → ... → 2.2.0-beta.n
    ↓ (beta testing ready, no new features)
2.2.0-rc.1 → 2.2.0-rc.2 → ... → 2.2.0-rc.n
    ↓ (final testing ready)
2.2.0[+build.123]
```

### When to Use Each Stage

#### Development (`dev`)
- **Purpose**: Early development and testing
- **When to use**: During active development of new features
- **Audience**: Developers and internal testing
- **Stability**: Unstable, may contain breaking changes

#### Alpha (`alpha`)
- **Purpose**: Initial testing phase
- **When to use**: Feature-complete but needs initial testing
- **Audience**: Internal testing team
- **Stability**: Mostly stable, major bugs fixed

#### Beta (`beta`)
- **Purpose**: Public testing phase
- **When to use**: Ready for broader testing, no new features added
- **Audience**: Beta testers, early adopters
- **Stability**: Stable, only bug fixes

#### Release Candidate (`rc`)
- **Purpose**: Final testing before release
- **When to use**: All testing complete, ready for production
- **Audience**: Final validation team
- **Stability**: Production-ready

#### Final Release
- **Purpose**: Production release
- **When to use**: Passed all testing and validation
- **Audience**: All users
- **Stability**: Fully stable and supported

## Version Management Tools

### Version Manager Script

The `scripts/version-manager.py` script provides command-line tools for version management:

```bash
# Show current version
python scripts/version-manager.py current

# Bump version components
python scripts/version-manager.py bump major     # 2.2.0 → 3.0.0
python scripts/version-manager.py bump minor     # 2.2.0 → 2.3.0
python scripts/version-manager.py bump patch     # 2.2.0 → 2.2.1
python scripts/version-manager.py bump prerelease  # 2.2.0-dev.1 → 2.2.0-dev.2

# Move to next development stage
python scripts/version-manager.py next-stage     # dev → alpha → beta → rc → final

# Validate version string
python scripts/version-manager.py validate "2.2.0-dev.1"

# Set specific version
python scripts/version-manager.py set "2.2.0-alpha.1"

# Show version information
python scripts/version-manager.py info
```

### Version Classes

#### Python (Version class in `src/py/bbctrl/version.py`)

```python
from bbctrl.version import Version

# Parse version
version = Version("2.2.0-dev.1")

# Check properties
print(version.is_prerelease())      # True
print(version.is_development())     # True
print(version.get_stage())          # "development"

# Version operations
next_version = version.bump_prerelease()  # 2.2.0-dev.2
final_version = version.to_final()        # 2.2.0
next_stage = version.next_stage()         # 2.2.0-alpha.1

# Comparison
version1 = Version("2.2.0-dev.1")
version2 = Version("2.2.0-alpha.1")
print(version1 < version2)  # True (dev < alpha)
```

#### JavaScript (Version class in `src/js/version.js`)

```javascript
// Parse version
const version = new Version("2.2.0-dev.1");

// Check properties
console.log(version.isPrerelease());      // true
console.log(version.isDevelopment());     // true
console.log(version.getStage());          // "development"

// Version operations
const nextVersion = version.bumpPrerelease();  // 2.2.0-dev.2
const finalVersion = version.toFinal();        // 2.2.0
const nextStage = version.nextStage();         // 2.2.0-alpha.1

// Comparison
const version1 = new Version("2.2.0-dev.1");
const version2 = new Version("2.2.0-alpha.1");
console.log(version1.lt(version2));  // true (dev < alpha)
```

## Version Comparison Rules

Versions are compared according to SemVer rules:

1. **Major, Minor, Patch**: Numeric comparison
2. **Pre-release precedence**: `dev < alpha < beta < rc < final`
3. **Build metadata**: Ignored for comparison purposes

### Examples

```python
# These are ordered from lowest to highest precedence
Version("2.2.0-dev.1") < Version("2.2.0-dev.2")     # True
Version("2.2.0-dev.2") < Version("2.2.0-alpha.1")   # True
Version("2.2.0-alpha.1") < Version("2.2.0-beta.1")  # True
Version("2.2.0-beta.1") < Version("2.2.0-rc.1")     # True
Version("2.2.0-rc.1") < Version("2.2.0")            # True
Version("2.2.0") < Version("2.3.0")                 # True
```

## Web UI Features

### Version Display

The web interface now shows:
- Current version number
- Version stage indicator with color coding
- Upgrade notifications with stage information

### Version Stage Indicators

| Stage | Color | Description |
|-------|-------|-------------|
| Development | Red | Early development |
| Alpha | Yellow | Initial testing |
| Beta | Green | Public testing |
| Release Candidate | Teal | Final testing |
| Final | Gray | Production release |

### Upgrade Dialog

The firmware upgrade dialog now shows:
- Current version stage
- Target version stage
- Visual indicators for both versions

## Configuration Management

### Backward Compatibility

The system maintains backward compatibility with existing version formats:
- Legacy tuple-based versions are automatically converted
- Existing configuration files continue to work
- Version comparison falls back to legacy logic when needed

### Configuration Upgrade

The system automatically upgrades configuration files when version changes require it, following the same rules as before but with enhanced version comparison.

## Build Integration

### Makefile Integration

The Makefile automatically reads version from `package.json`:

```makefile
VERSION := $(shell sed -n 's/^.*"version": "\([^\"]*\)",.*$$/\1/p' package.json)
```

### Package Files

Version information is maintained in:
- `package.json`: Main version for Node.js/npm
- `src/py/bbctrl.egg-info/PKG-INFO`: Python package version
- Both files are kept in sync using the version manager script

## Best Practices

### Development Workflow

1. **Start new features**: Create `dev.1` version
2. **Feature complete**: Move to `alpha.1`
3. **Initial testing**: Increment alpha versions as needed
4. **Public testing**: Move to `beta.1`
5. **Final validation**: Move to `rc.1`
6. **Production release**: Remove prerelease identifier

### Version Bumping

- **Major**: Breaking changes, API changes
- **Minor**: New features, backward compatible
- **Patch**: Bug fixes, backward compatible
- **Prerelease**: Increment within same stage

### Commit Messages

Use conventional commit format with version context:

```bash
feat: add new CNC feature (2.2.0-dev.1)
fix: resolve motor calibration issue (2.2.0-dev.2)
refactor: improve version comparison logic (2.2.0-alpha.1)
```

## Migration from Legacy System

### Automatic Migration

The system automatically handles migration from the legacy versioning system:
- Existing versions are parsed and converted
- Configuration files are upgraded transparently
- No manual intervention required

### Version History

Legacy versions are mapped as follows:
- `2.0.5` → `2.0.5` (unchanged)
- `2.0.6` → `2.0.6` (unchanged)

New development starts with appropriate pre-release identifiers.

## Troubleshooting

### Common Issues

#### Invalid Version Format
```
Error: Invalid version format: 2.2.0-invalid
```
**Solution**: Use valid SemVer format with supported pre-release identifiers

#### Version Comparison Issues
```
Version comparison failed between legacy and SemVer versions
```
**Solution**: The system automatically falls back to legacy comparison

#### Build Metadata Not Displayed
Build metadata (e.g., `+build.123`) is not shown in UI but is preserved in version objects.

### Validation

Use the version manager script to validate versions:

```bash
python scripts/version-manager.py validate "2.2.0-dev.1"
# Output: ✓ Valid version: 2.2.0-dev.1
```

## Examples

### Complete Development Cycle

```bash
# Start development
python scripts/version-manager.py set "2.2.0-dev.1"

# Development iterations
python scripts/version-manager.py bump prerelease  # 2.2.0-dev.2
python scripts/version-manager.py bump prerelease  # 2.2.0-dev.3

# Move to alpha
python scripts/version-manager.py next-stage       # 2.2.0-alpha.1

# Alpha testing
python scripts/version-manager.py bump prerelease  # 2.2.0-alpha.2

# Move to beta
python scripts/version-manager.py next-stage       # 2.2.0-beta.1

# Final release
python scripts/version-manager.py next-stage       # 2.2.0-rc.1
python scripts/version-manager.py next-stage       # 2.2.0
```

### Version Parsing Examples

```python
from bbctrl.version import Version

# Basic version
v1 = Version("2.2.0")
print(v1.get_stage())  # "final"

# Development version
v2 = Version("2.2.0-dev.1")
print(v2.get_stage())  # "development"
print(v2.is_prerelease())  # True

# Release candidate with build metadata
v3 = Version("2.2.0-rc.1+build.123")
print(v3.get_stage())  # "release-candidate"
print(v3.build)  # "build.123"
```

This semantic versioning system provides clear communication about software maturity and enables better development workflows for the Buildbotics CNC Controller.