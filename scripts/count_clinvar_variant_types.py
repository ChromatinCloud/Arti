#!/usr/bin/env python3
"""
Count variant types in ClinVar files to understand what we're processing
"""

import pandas as pd
from pathlib import Path
from collections import defaultdict

def count_variant_types():
    clinvar_dir = Path("/Users/lauferva/Desktop/Arti/.refs/clinical_evidence/clinvar/clinvar_by_significance/")
    
    total_counts = defaultdict(int)
    file_counts = {}
    
    for clinvar_file in sorted(clinvar_dir.glob("*.tsv")):
        print(f"Scanning {clinvar_file.name}...")
        
        # Read in chunks to handle large files
        counts = defaultdict(int)
        chunk_size = 100000
        
        for chunk in pd.read_csv(clinvar_file, sep='\t', chunksize=chunk_size, low_memory=False):
            # Count variant types
            for vtype in chunk['Type'].value_counts().items():
                counts[vtype[0]] += vtype[1]
                total_counts[vtype[0]] += vtype[1]
        
        file_counts[clinvar_file.name] = dict(counts)
        
        # Show top types for this file
        print(f"  Total variants: {sum(counts.values())}")
        sorted_types = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        for vtype, count in sorted_types[:5]:
            print(f"    {vtype}: {count:,}")
        print()
    
    # Show overall summary
    print("="*60)
    print("OVERALL VARIANT TYPE DISTRIBUTION")
    print("="*60)
    
    sorted_total = sorted(total_counts.items(), key=lambda x: x[1], reverse=True)
    total_variants = sum(total_counts.values())
    
    for vtype, count in sorted_total:
        percentage = (count / total_variants) * 100
        print(f"{vtype:.<40} {count:>12,} ({percentage:>5.1f}%)")
    
    print(f"\n{'TOTAL':.<40} {total_variants:>12,}")
    
    # Check which types we're not handling
    known_types = {
        'single nucleotide variant', 'Deletion', 'Duplication', 
        'Insertion', 'Indel', 'Microsatellite', 'Inversion'
    }
    
    unknown_types = [t for t in total_counts.keys() if t not in known_types]
    if unknown_types:
        print(f"\nUnhandled variant types:")
        for vtype in unknown_types:
            print(f"  - {vtype}: {total_counts[vtype]:,}")

if __name__ == "__main__":
    count_variant_types()