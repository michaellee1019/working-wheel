# Release Process

## Overview

Both the Viam module and get_token helper binaries are released together using the same semver tag.

## Process

### 1. Create and Push a Tag

```bash
# Tag format: X.Y.Z (semver)
git tag 1.0.0
git push origin 1.0.0
```

### 2. GitHub Actions Workflows Trigger

Two workflows run **in parallel** when a tag is pushed:

#### Workflow 1: `deploy.yml` (Viam Module)
- Builds the Viam module for all supported architectures
- Publishes to Viam registry
- Creates a GitHub release

#### Workflow 2: `build-get-token.yml` (Helper Binaries)
- Builds get_token binaries for:
  - `linux-amd64`
  - `linux-arm64` 
  - `darwin-arm64`
- Adds binaries to the same GitHub release

### 3. Result

A single GitHub release is created containing:
- ✅ Viam module deployment (published to registry)
- ✅ Three get_token binaries (attached as release assets)
- ✅ Release notes with usage instructions

## Release Assets

Each release will include:

```
Release v1.0.0
├── Module (deployed to Viam registry)
└── Binaries (attached to release)
    ├── get_token-linux-amd64
    ├── get_token-linux-arm64
    └── get_token-darwin-arm64
```

## For Users

### Using the Module
```bash
# Add to your Viam machine via app.viam.com
# Search for: michaellee1019:working-wheel:google-calender-service
```

### Using get_token Binary
```bash
# Download from releases page
wget https://github.com/USER/REPO/releases/download/1.0.0/get_token-linux-amd64
chmod +x get_token-linux-amd64
./get_token-linux-amd64
```

## Testing Releases

To test without affecting production:

```bash
# Use a pre-release version
git tag 0.0.1-alpha
git push origin 0.0.1-alpha
```

This will:
- Trigger both workflows
- Create a release marked as "pre-release"
- Not be shown as the latest release

## Versioning

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (1.0.0): Breaking changes
- **MINOR** (0.1.0): New features, backward compatible
- **PATCH** (0.0.1): Bug fixes, backward compatible

Examples:
- `1.0.0` - Initial stable release
- `1.1.0` - Added new calendar status types
- `1.1.1` - Fixed timezone handling bug
- `2.0.0` - Changed API interface (breaking)

