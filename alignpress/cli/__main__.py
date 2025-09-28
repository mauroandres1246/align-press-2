"""
Entry point for CLI module execution.

This allows running the main CLI interface as:
python -m alignpress.cli
"""

import sys
from .main import main

if __name__ == '__main__':
    sys.exit(main())