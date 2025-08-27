# Build Info System for Buildbotics CNC Controller

This document explains how the build info system works and how it ensures consistent build metadata across different build environments.

## Problem Solved

Previously, when developers committed changes before building, the build info (commit hash) would reflect the *new* commit rather than the state of the code that was actually built. This caused confusion about which version of the code was in each build artifact.

## Solution Overview

The build info system uses a **pre-commit hook** to capture build metadata *before* changes are committed, ensuring that build artifacts always reflect the exact state of the code that was built.

## How It Works

### 1. Pre-commit Hook (`.git/hooks/pre-commit`)

When you run `git commit`, the pre-commit hook automatically:

- Captures the current commit hash (`git rev-parse --short HEAD`)
- Records the build timestamp in UTC
- Creates a `.build-info.json` file with this metadata
- Stages the build info file so it's included in the commit

**Example `.build-info.json`:**
```json
{
  "commit": "4007368f",
  "build_time": "20250827-171439",
  "build_timestamp": "2025-08-27T17:14:39Z",
  "git_status": "4 changes"
}
```

### 2. Build Process Integration

The build system automatically reads the `.build-info.json` file and incorporates it into version numbers:

#### Makefile Integration
```makefile
# Check if build info exists and use it
BUILD_INFO_EXISTS := $(shell test -f .build-info.json && echo "yes" || echo "no")
ifeq ($(BUILD_INFO_EXISTS),yes)
  BUILD_COMMIT := $(shell cat .build-info.json | grep -o '"commit": "[^"]*' | cut -d'"' -f4)
  BUILD_TIME := $(shell cat .build-info.json | grep -o '"build_time": "[^"]*' | cut -d'"' -f4)
  BASE_VERSION := $(shell sed -n 's/^.*"version": "\([^\"]*\)",.*$$/\1/p' package.json)
  VERSION := $(BASE_VERSION)+build.$(BUILD_COMMIT).$(BUILD_TIME)
endif
```

#### Setup.py Integration
```python
# Check for build info and enhance version
version = pkg['version']
if os.path.exists('.build-info.json'):
    try:
        with open('.build-info.json', 'r') as f:
            build_info = json.load(f)
            commit = build_info.get('commit', '')
            build_time = build_info.get('build_time', '')
            if commit and build_time:
                version = f"{version}+build.{commit}.{build_time}"
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Warning: Could not read build info: {e}")
```

### 3. Version Format

Builds now include build metadata in the version string:
```
2.1.0-dev.2+build.4007368f.20250827-171439
         │     │         │
         │     │         └── Build timestamp
         │     └──────────── Commit hash (short)
         └────────────────── Base version from package.json
```

## Workflow

### Normal Development Workflow

1. **Make changes** to your code
2. **Run `git commit`** - the pre-commit hook captures build info
3. **Run `./scripts/docker-build`** - build uses captured info
4. **Package name** will include the commit hash and timestamp

### Example Output

```bash
$ git commit -m "Add new feature"
Capturing build info for commit a1b2c3d4
Build info captured and staged
Commit: a1b2c3d4
Build Time: 2025-08-27T17:14:39Z

$ ./scripts/docker-build
Using build info: 2.1.0-dev.2+build.a1b2c3d4.20250827-171439
[... build output ...]

$ ls dist/
bbctrl-2.1.0-dev.2+build.a1b2c3d4.20250827-171439.tar.bz2
```

## Comparison with Other Systems

### Apple (iOS/macOS)
- Uses `CFBundleVersion` (build number) and `CFBundleShortVersionString` (marketing version)
- Build numbers are auto-incremented by Xcode
- Captured at build time, not commit time

### Android
- Uses `versionCode` (integer, auto-incremented) and `versionName` (string)
- Build metadata captured during Gradle build process

### Our Solution
- **Pre-commit capture**: Like Apple's approach, captures info before commit
- **Git integration**: Uses actual commit hashes for traceability
- **Build-time enhancement**: Like Android, enhances version during build
- **Cross-platform**: Works in Docker, native builds, and CI/CD

## Benefits

1. **Traceability**: Every build artifact is linked to a specific commit
2. **Reproducibility**: You can checkout the exact commit that was built
3. **CI/CD Integration**: Build info works across different build environments
4. **Debugging**: Easy to identify which code version is in production
5. **Consistency**: Same build info regardless of when you build after commit

## Files Modified

- `.git/hooks/pre-commit` - Captures build info before commits
- `Makefile` - Reads build info and includes in version
- `setup.py` - Enhances package version with build metadata
- `.build-info.json` - Stores captured build information (auto-generated)

## Testing

Run the test script to verify the system works:

```bash
./test-build-info.sh
```

This will:
- Simulate the pre-commit hook
- Test Makefile version parsing
- Test setup.py version enhancement
- Verify the complete workflow

## Troubleshooting

### Build Info Not Found
If builds don't include build metadata:
1. Check if `.build-info.json` exists
2. Verify the pre-commit hook is executable: `ls -la .git/hooks/pre-commit`
3. Make sure you committed after the hook was installed

### Version Parsing Errors
If you see version parsing warnings:
- The build info JSON may be malformed
- Check `.build-info.json` for valid JSON format
- The system falls back to base version if parsing fails

### Docker Builds
For Docker builds, the `.build-info.json` file must be in the build context. The current Docker setup already includes the entire working directory, so this works automatically.

## Migration Notes

- Existing builds without build info will use the base version from `package.json`
- The system is backward compatible - old builds continue to work
- No changes needed to existing deployment or update scripts
- Build info is optional - builds work with or without it

## Future Enhancements

Potential improvements:
- Include build machine info (hostname, OS)
- Add build duration tracking
- Integrate with CI/CD pipeline metadata
- Add build artifact signing/checksums
- Include dependency versions in build info