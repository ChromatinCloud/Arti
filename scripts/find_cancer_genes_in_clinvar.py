#!/usr/bin/env python3
"""
Quick scan to find known cancer genes in ClinVar files
"""

import pandas as pd
from pathlib import Path

# Common cancer genes
CANCER_GENES = {
    'TP53', 'KRAS', 'BRAF', 'PIK3CA', 'PTEN', 'APC', 'EGFR', 'BRCA1', 'BRCA2',
    'ALK', 'RET', 'MET', 'ERBB2', 'CDH1', 'VHL', 'MLH1', 'MSH2', 'MSH6', 'PMS2',
    'ATM', 'CHEK2', 'PALB2', 'RAD51C', 'RAD51D', 'BRIP1', 'NBN', 'NF1', 'NF2',
    'RB1', 'CDKN2A', 'MYC', 'MYCN', 'KIT', 'PDGFRA', 'FLT3', 'JAK2', 'MPL',
    'CALR', 'CSF3R', 'SETBP1', 'SF3B1', 'SRSF2', 'U2AF1', 'ZRSR2', 'ASXL1',
    'EZH2', 'IDH1', 'IDH2', 'DNMT3A', 'TET2', 'NPM1', 'CEBPA', 'RUNX1'
}

def scan_clinvar_file(file_path: Path):
    """Scan a ClinVar file for cancer genes"""
    print(f"\nScanning {file_path.name}...")
    
    # Read first 50000 rows to get a sample
    df = pd.read_csv(file_path, sep='\t', nrows=50000)
    
    # Filter for cancer genes
    df_cancer = df[df['GeneSymbol'].isin(CANCER_GENES)]
    
    if len(df_cancer) > 0:
        print(f"  Found {len(df_cancer)} variants in cancer genes (out of {len(df)} total)")
        print(f"  Cancer genes found: {', '.join(sorted(df_cancer['GeneSymbol'].unique()))}")
        
        # Show some examples
        print("\n  Example variants:")
        for idx, row in df_cancer.head(5).iterrows():
            print(f"    {row['GeneSymbol']}: {row['Name'][:80]}...")
    else:
        print(f"  No cancer gene variants found in first {len(df)} rows")
    
    return len(df_cancer), len(df)

def main():
    clinvar_dir = Path("/Users/lauferva/Desktop/Arti/.refs/clinical_evidence/clinvar/clinvar_by_significance/")
    
    print("Scanning ClinVar files for known cancer genes...")
    print(f"Looking for {len(CANCER_GENES)} cancer genes")
    
    total_cancer = 0
    total_variants = 0
    
    for clinvar_file in sorted(clinvar_dir.glob("*.tsv")):
        cancer_count, variant_count = scan_clinvar_file(clinvar_file)
        total_cancer += cancer_count
        total_variants += variant_count
    
    print(f"\n{'='*80}")
    print(f"TOTAL: {total_cancer} cancer gene variants out of {total_variants} variants scanned")
    print(f"Percentage: {(total_cancer/total_variants)*100:.2f}%")
    
    print("\nNote: This is based on first 50K variants per file. Actual counts may be higher.")

if __name__ == "__main__":
    main()