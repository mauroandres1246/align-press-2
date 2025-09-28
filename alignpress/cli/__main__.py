"""
Entry point for CLI module execution.

This allows running the CLI tools as:
python -m alignpress.cli.test_detector
"""

import sys
from .test_detector import main

if __name__ == '__main__':
    sys.exit(main())