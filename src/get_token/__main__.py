#!/usr/bin/env python3
"""Entry point for the get_token package."""

import sys
import os

# When running as a package from command line (python -m get_token)
if __name__ == '__main__' and __package__ is None:
    # Add parent directory to path to enable relative imports
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    __package__ = 'get_token'

# Use relative import when running as package, absolute when frozen
if getattr(sys, 'frozen', False):
    # Running as PyInstaller executable - main.py is in the same bundle
    # Import directly from the bundled main module
    import main as main_module
    main_func = main_module.main
else:
    # Running as script or package
    from .main import main as main_func

if __name__ == '__main__':
    main_func()

