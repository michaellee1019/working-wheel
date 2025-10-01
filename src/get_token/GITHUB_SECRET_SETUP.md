# Setting Up GitHub Secret for Bundled Credentials

## Overview

The `get_token` binary can include default Google OAuth credentials bundled inside the executable. This allows users to run the binary without needing to download their own `credentials.json` file (though they can still provide their own if desired).

## Security Note

The credentials.json file contains your OAuth **client ID** and **client secret**, which are considered **public information** for desktop applications. According to Google's OAuth 2.0 documentation, these values can be safely distributed with your application because:

1. They identify your application to Google, not the user
2. They cannot be used to access user data without user consent
3. The actual authentication happens through the OAuth flow where the user logs in

However, storing them as a GitHub secret keeps them out of your repository history and makes them easier to rotate if needed.

## Steps to Set Up the Secret

### 1. Get Your credentials.json File

If you don't have one yet:

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create a new project or select an existing one
3. Enable the Google Calendar API
4. Create OAuth 2.0 Client ID
   - Application type: **Desktop app**
   - Name: Something like "Working Wheel Token Generator"
5. Download the credentials file

### 2. Copy the credentials.json Content

Open the downloaded `credentials.json` file. It should look like:

```json
{
  "installed": {
    "client_id": "123456789.apps.googleusercontent.com",
    "project_id": "your-project",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "YOUR_CLIENT_SECRET",
    "redirect_uris": ["http://localhost"]
  }
}
```

### 3. Add as GitHub Secret

1. Go to your GitHub repository
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `GOOGLE_OAUTH_CREDENTIALS`
5. Value: Paste the entire contents of your `credentials.json` file
6. Click **Add secret**

### 4. Test the Build

The next time you push a tag (e.g., `1.0.0`), the workflow will:

1. Create `default_credentials.json` from the secret
2. Build the binary with PyInstaller, bundling the credentials inside
3. Users can run the binary without providing their own credentials

**Note:** The PyInstaller spec file is generated dynamically during the build, so you don't need to maintain it in the repository.

## Usage for End Users

### With Bundled Credentials (Default)

If the binary was built with the secret:

```bash
# Just run it - no credentials.json needed!
./get_token-linux-amd64
```

### With Custom Credentials

Users can still provide their own credentials:

```bash
# Option 1: Place credentials.json in current directory
cp my_credentials.json credentials.json
./get_token-linux-amd64

# Option 2: Specify path with flag
./get_token-linux-amd64 --credentials /path/to/my_credentials.json
```

## Priority Order

The tool looks for credentials in this order:

1. Path specified with `--credentials` flag
2. `credentials.json` in current directory
3. Bundled `default_credentials.json` (if available)

## Updating the Credentials

If you need to rotate or update your OAuth credentials:

1. Create new credentials in Google Cloud Console
2. Update the `GOOGLE_OAUTH_CREDENTIALS` secret in GitHub
3. Create a new release tag

The new binaries will include the updated credentials.

## Building Without Secrets

If the `GOOGLE_OAUTH_CREDENTIALS` secret is not set:

- The workflow will still build successfully
- The binary will not have bundled credentials
- Users will need to provide their own `credentials.json` file

This is useful for:
- Testing builds
- Distributing to users who want to use their own OAuth application
- Open source contributions where secrets aren't available

