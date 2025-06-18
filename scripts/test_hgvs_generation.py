#!/usr/bin/env python3
"""
Test HGVS generation logic with sample ClinVar data
"""

import pandas as pd
from pathlib import Path

# Import the HGVS generation function
import sys
sys.path.append(str(Path(__file__).parent))
from clinvar_to_oncokb import create_hgvsg

def test_hgvs_generation():
    """Test HGVS generation with different variant types"""
    
    # Test cases based on actual ClinVar data
    test_cases = [
        # SNV
        {
            'Chromosome': '7',
            'Start': 140753336,
            'Stop': 140753336,
            'ReferenceAlleleVCF': 'T',
            'AlternateAlleleVCF': 'A',
            'Type': 'single nucleotide variant'
        },
        # Deletion
        {
            'Chromosome': '7',
            'Start': 55174771,
            'Stop': 55174785,
            'ReferenceAlleleVCF': 'CTTTCAGACAGGTCT',
            'AlternateAlleleVCF': 'C',
            'Type': 'Deletion'
        },
        # Duplication
        {
            'Chromosome': '7',
            'Start': 55181318,
            'Stop': 55181326,
            'ReferenceAlleleVCF': 'C',
            'AlternateAlleleVCF': 'CTGTGAAATA',
            'Type': 'Duplication'
        },
        # Insertion
        {
            'Chromosome': '12',
            'Start': 25245350,
            'Stop': 25245351,
            'ReferenceAlleleVCF': 'C',
            'AlternateAlleleVCF': 'CGT',
            'Type': 'Insertion'
        },
        # Complex Indel
        {
            'Chromosome': '7',
            'Start': 4781213,
            'Stop': 4781216,
            'ReferenceAlleleVCF': 'GGAT',
            'AlternateAlleleVCF': 'TGCTGTAAACTGTAACTGTAAA',
            'Type': 'Indel'
        }
    ]
    
    print("Testing HGVS generation:\n")
    
    for i, test_case in enumerate(test_cases, 1):
        # Create a pandas Series to simulate a row
        row = pd.Series(test_case)
        hgvs = create_hgvsg(row)
        
        print(f"Test {i}: {test_case['Type']}")
        print(f"  Input: Chr{test_case['Chromosome']}:{test_case['Start']}-{test_case['Stop']} {test_case['ReferenceAlleleVCF']}>{test_case['AlternateAlleleVCF']}")
        print(f"  HGVS: {hgvs}")
        print()

    # Test with a small sample from actual ClinVar file
    print("\nTesting with actual ClinVar data:")
    
    clinvar_file = Path("/Users/lauferva/Desktop/Arti/.refs/clinical_evidence/clinvar/clinvar_by_significance/PLP.tsv")
    
    if clinvar_file.exists():
        df = pd.read_csv(clinvar_file, sep='\t', nrows=10)
        df_grch38 = df[df['Assembly'] == 'GRCh38']
        
        for idx, row in df_grch38.iterrows():
            hgvs = create_hgvsg(row)
            if hgvs:
                print(f"  {row['Type']}: {hgvs}")

if __name__ == "__main__":
    test_hgvs_generation()