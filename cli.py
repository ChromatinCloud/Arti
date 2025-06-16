#!/usr/bin/env python3
"""
Annotation Engine CLI Entry Point

Simple wrapper for the main CLI module to enable direct execution.
This script automatically uses the poetry environment.
"""

import subprocess
import sys
from pathlib import Path

def main():
    """Run the annotation engine CLI using poetry"""
    # Get the directory containing this script
    script_dir = Path(__file__).parent
    
    # Build the poetry command
    cmd = [
        "poetry", "run", "annotation-engine"
    ] + sys.argv[1:]  # Pass through all CLI arguments
    
    try:
        # Execute using poetry
        result = subprocess.run(cmd, cwd=script_dir)
        return result.returncode
    except FileNotFoundError:
        print("Error: Poetry not found. Please install poetry or use 'poetry run annotation-engine' directly.")
        return 1
    except Exception as e:
        print(f"Error running annotation engine: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())