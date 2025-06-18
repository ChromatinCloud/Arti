#!/usr/bin/env python3
"""
Process just the PLP (Pathogenic/Likely Pathogenic) ClinVar file
This is where we're most likely to find OncoKB annotations
"""

import subprocess
import sys
from pathlib import Path

def main():
    # First, let's process a subset of PLP file
    print("Creating subset of PLP file for processing...")
    
    # Take first 10,000 variants from PLP
    plp_file = Path("/Users/lauferva/Desktop/Arti/.refs/clinical_evidence/clinvar/clinvar_by_significance/PLP.tsv")
    subset_file = Path("/tmp/PLP_subset.tsv")
    
    # Create subset
    subprocess.run(f"head -10000 {plp_file} > {subset_file}", shell=True, check=True)
    
    # Run the main processing script on this subset
    print("\nProcessing PLP subset through OncoKB API...")
    
    # Import and run the processing function
    sys.path.append(str(Path(__file__).parent))
    from clinvar_to_oncokb import process_clinvar_file
    
    output_file = Path("/tmp/PLP_subset_oncokb.tsv")
    process_clinvar_file(subset_file, output_file)
    
    # Now analyze the results
    print("\nAnalyzing OncoKB results...")
    from analyze_oncokb_results import process_oncokb_file
    
    no_data_log = Path("/tmp/plp_no_oncokb_data.log")
    tabular_output = Path("/tmp/plp_oncokb_annotations.tsv")
    
    process_oncokb_file(output_file, no_data_log, tabular_output)
    
    # Show summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    if tabular_output.exists():
        import pandas as pd
        df = pd.read_csv(tabular_output, sep='\t')
        print(f"\nFound {len(df)} OncoKB annotations")
        
        if len(df) > 0:
            print("\nTop genes with OncoKB annotations:")
            print(df['gene'].value_counts().head(10))
            
            print("\nOncogenic classifications:")
            if 'oncogenic' in df.columns:
                print(df['oncogenic'].value_counts())
                
            print("\nSample annotations:")
            for idx, row in df.head(5).iterrows():
                print(f"\n{row['gene']} - {row['alteration']} - {row['oncogenic']}")
                if row.get('treatmentDrugs'):
                    print(f"  Treatment: {row['treatmentDrugs']} (Level {row['treatmentLevel']})")
    
    print(f"\nLog of variants without OncoKB data: {no_data_log}")
    
    # Show first few entries from no-data log
    if no_data_log.exists():
        print("\nFirst few variants without OncoKB data:")
        with open(no_data_log, 'r') as f:
            lines = f.readlines()
            for line in lines[5:15]:  # Skip header lines
                if line.strip() and '|' in line:
                    print(f"  {line.strip()}")

if __name__ == "__main__":
    main()