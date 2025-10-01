#!/usr/bin/env python3
"""Entry point for the get_token package."""

# Use absolute import for PyInstaller compatibility
import sys
import os

# Add the package directory to the path
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    bundle_dir = sys._MEIPASS
else:
    # Running as script
    bundle_dir = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, bundle_dir)

# Now import main directly
from main import main

if __name__ == '__main__':
    main()

