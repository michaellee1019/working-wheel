#!/usr/bin/env python3
"""
Google Calendar OAuth Token Generator

This script:
1. Reads credentials.json (Google OAuth client secrets)
2. Runs the OAuth flow to authenticate
3. Generates a do_command payload for the Viam module
4. Prints the payload and copies it to clipboard

Usage:
    python -m get_token
    
Prerequisites:
    - credentials.json file in the current directory
    - Install dependencies: pip install google-auth-oauthlib pyperclip
"""

from __future__ import print_function

import json
import os
import os.path
import sys
import argparse

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# If modifying these scopes, delete any existing token files
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']


def get_bundled_credentials_path():
    """Get the path to bundled credentials.json file."""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        bundle_dir = sys._MEIPASS
    else:
        # Running as script
        bundle_dir = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(bundle_dir, 'default_credentials.json')


def find_credentials_file(custom_path=None):
    """Find credentials.json file in order of precedence.
    
    Priority:
    1. Custom path provided by user
    2. credentials.json in current directory
    3. Bundled default_credentials.json
    
    Args:
        custom_path: Optional path to credentials file
        
    Returns:
        Path to credentials file, or None if not found
    """
    # Check custom path first
    if custom_path:
        if os.path.exists(custom_path):
            print(f"Using credentials from: {custom_path}")
            return custom_path
        else:
            print(f"Warning: Specified credentials file not found: {custom_path}")
    
    # Check current directory
    if os.path.exists('credentials.json'):
        print("Using credentials from: ./credentials.json")
        return 'credentials.json'
    
    # Check bundled credentials
    bundled_path = get_bundled_credentials_path()
    if os.path.exists(bundled_path):
        print("Using bundled default credentials")
        return bundled_path
    
    return None


def get_credentials(credentials_path=None):
    """Run OAuth flow to get Google Calendar credentials.
    
    Args:
        credentials_path: Optional path to credentials.json file
        
    Returns:
        Credentials object or None if authentication fails
    """
    creds = None
    
    # Find credentials file
    creds_file = find_credentials_file(credentials_path)
    
    if not creds_file:
        print("\nERROR: No credentials.json file found!")
        print("\nOptions:")
        print("1. Place your credentials.json in the current directory")
        print("2. Specify a custom path: get_token --credentials /path/to/credentials.json")
        print("3. Use the bundled default credentials (if available)")
        print("\nTo get credentials:")
        print("  1. Go to https://console.cloud.google.com/apis/credentials")
        print("  2. Create OAuth 2.0 Client ID (Desktop app)")
        print("  3. Download as credentials.json")
        return None
    
    print("\nStarting OAuth flow...")
    print("A browser window will open for authentication.")
    
    try:
        flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
        creds = flow.run_local_server(port=0)
        print("\n✓ Authentication successful!")
        return creds
    except Exception as e:
        print(f"\n✗ Authentication failed: {e}")
        return None


def credentials_to_dict(creds: Credentials) -> dict:
    """Convert Credentials object to dictionary."""
    # Parse the JSON string to get the credentials as a dict
    creds_json = creds.to_json()
    return json.loads(creds_json)


def create_do_command_payload(creds_dict: dict) -> dict:
    """Create the do_command payload for Viam module."""
    return {
        "set_credentials": creds_dict
    }


def main():
    """Main entry point for the token generator."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Generate Google Calendar OAuth tokens for Viam module',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use credentials.json from current directory
  get_token

  # Use bundled default credentials (if available)
  get_token

  # Use custom credentials file
  get_token --credentials /path/to/my_credentials.json
        """
    )
    parser.add_argument(
        '--credentials', '-c',
        metavar='PATH',
        help='Path to credentials.json file (default: ./credentials.json or bundled)'
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("Google Calendar OAuth Token Generator")
    print("=" * 70)
    print()
    
    # Get credentials through OAuth flow
    creds = get_credentials(credentials_path=args.credentials)
    if not creds:
        return
    
    # Convert to dictionary
    creds_dict = credentials_to_dict(creds)
    
    # Create do_command payload
    payload = create_do_command_payload(creds_dict)
    payload_json = json.dumps(payload, indent=2)
    
    print("\n" + "=" * 70)
    print("DO_COMMAND PAYLOAD")
    print("=" * 70)
    print(payload_json)
    print("=" * 70)
    
    # Try to copy to clipboard
    try:
        import pyperclip
        pyperclip.copy(payload_json)
        print("\n✓ Payload copied to clipboard!")
        print("Paste this into the DoCommand section of the google calendar service")
        print("on your viam machine at app.viam.com")
    except ImportError:
        print("\n⚠ pyperclip not installed. To enable clipboard copy:")
        print("  pip install pyperclip")
    except Exception as e:
        print(f"\n⚠ Could not copy to clipboard: {e}")
    
    print()


if __name__ == '__main__':
    main()

