#!/usr/bin/env python3
"""Entry point for the get_token package."""

import sys
import os

# When running as a package from command line (python -m get_token)
if __name__ == '__main__' and __package__ is None:
    # Add parent directory to path to enable relative imports
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    __package__ = 'get_token'

# Import the main function
if getattr(sys, 'frozen', False):
    # Running as PyInstaller executable
    import get_token_main
    main_func = get_token_main.main
else:
    # Running as script or package
    from .get_token_main import main as main_func

if __name__ == '__main__':
    main_func()

