"""
Main entry point for the Annotation Engine CLI

Allows running the CLI via: python -m annotation_engine
"""

import sys
from .cli import main

if __name__ == '__main__':
    sys.exit(main())