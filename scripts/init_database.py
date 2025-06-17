#!/usr/bin/env python3
"""
Database initialization script for Annotation Engine

Creates SQLite database and populates with synthetic interpretation data.
"""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from annotation_engine.db.init_db import initialize_annotation_database

def main():
    """Initialize the annotation database"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("Initializing Annotation Engine Database...")
    print("=" * 50)
    
    try:
        # Initialize database with reset
        initialize_annotation_database(reset=True)
        print("\n✅ Database initialization complete!")
        print("   - Schema created")
        print("   - Synthetic data loaded")
        print("   - Test case created")
        
    except Exception as e:
        print(f"\n❌ Database initialization failed: {e}")
        logging.exception("Database initialization error")
        sys.exit(1)

if __name__ == "__main__":
    main()