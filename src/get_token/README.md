# Google Calendar OAuth Token Generator

A utility to generate OAuth tokens for the Google Calendar Viam module.

## Installation

### Option 1: Use Pre-built Binary (Recommended)

Download the binary for your platform from the [releases page](https://github.com/michaellee1019/working-wheel/releases):

- **Linux AMD64**: `get_token-linux-amd64`
- **Linux ARM64**: `get_token-linux-arm64` (Raspberry Pi, etc.)
- **macOS ARM64**: `get_token-darwin-arm64` (Apple Silicon)

Make it executable:
```bash
chmod +x get_token-<platform>
```

### Option 2: Run from Source

```bash
# Install dependencies
pip install -r src/get_token/requirements.txt

# Run the package
python -m get_token

# Or use the wrapper script
python get_token.py
```

## Usage

### Option 1: Using Pre-built Binary (with bundled credentials)

If the binary was built with bundled credentials, you can run it directly:

```bash
# No credentials.json needed!
./get_token-<platform>
```

### Option 2: Using Your Own Credentials

1. **Get Google OAuth Credentials**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
   - Create a new project or select existing
   - Enable Google Calendar API
   - Create OAuth 2.0 Client ID (Desktop application)
   - Download as `credentials.json`

2. **Run with your credentials**:
   ```bash
   # Option A: Place credentials.json in current directory
   ./get_token-<platform>
   
   # Option B: Specify custom path
   ./get_token-<platform> --credentials /path/to/your/credentials.json
   ```

### Running from Source

```bash
python -m get_token [--credentials /path/to/credentials.json]
```

### Authentication Flow

1. A browser window will open
2. Sign in with your Google account
3. Grant calendar access
4. The tool displays a JSON payload
5. Payload is automatically copied to clipboard
6. Paste it into the `do_command` section of your Viam module

## Command Line Options

```bash
get_token [OPTIONS]

Options:
  -c, --credentials PATH  Path to credentials.json file
  -h, --help             Show help message
```

## Credentials Priority

The tool looks for credentials in this order:

1. **Custom path** (via `--credentials` flag)
2. **Current directory** (`./credentials.json`)
3. **Bundled credentials** (if available in the binary)

## Output

The tool generates a payload like:

```json
{
  "set_credentials": {
    "token": "ya29.a0...",
    "refresh_token": "1//0g...",
    "token_uri": "https://oauth2.googleapis.com/token",
    "client_id": "xxx.apps.googleusercontent.com",
    "client_secret": "xxx",
    "scopes": ["https://www.googleapis.com/auth/calendar.readonly"]
  }
}
```

Use this payload with the Viam module's `set_credentials` command.

## Development

### Building Binaries Locally

```bash
cd src/get_token
pip install -r requirements.txt
pip install pyinstaller

# Optional: Create default_credentials.json to bundle credentials
# cp your_credentials.json default_credentials.json

pyinstaller get_token.spec
```

The binary will be in `dist/get_token`.

### Setting Up Bundled Credentials (for Maintainers)

To include default credentials in the released binaries:

1. Add your `credentials.json` as a GitHub secret
2. Name it: `GOOGLE_OAUTH_CREDENTIALS`
3. The build workflow will automatically include it

See [GITHUB_SECRET_SETUP.md](GITHUB_SECRET_SETUP.md) for detailed instructions.

### Release Process

Create a semver tag (e.g., `1.0.0`):

```bash
git tag 1.0.0
git push origin 1.0.0
```

This triggers the GitHub Actions workflow to:
1. Build the Viam module (via `deploy.yml`)
2. Build get_token binaries for all platforms (via `build-get-token.yml`)

Both workflows run in parallel and the binaries are attached to the same release.

